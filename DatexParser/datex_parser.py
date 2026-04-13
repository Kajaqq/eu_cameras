"""DATEX II parser for Spanish DGT traffic situation data.

Downloads the DGT SituationPublication XML feed, parses every
``situationRecord`` into a :class:`TruckDashboardAlert`, and exposes
three filtering methods for downstream consumers (road, admin-area,
and GPS-radius queries).

Example::

    parser = DatexParser(downloader=GenericDownloader())
    alerts = await parser.get_parsed_data()
    nearby = parser.get_alerts_near(lat=38.98, lon=-5.53, radius=100)
"""

from __future__ import annotations

import json
from pathlib import Path

from lxml import etree

from Downloaders.base_downloader import GenericDownloader
from Parsers.base_parser import BaseParser
from tools.utils import haversine_km

from .datex_models import (
    NON_TRUCK_VEHICLE_TYPES,
    LocationPoint,
    TruckDashboardAlert,
)

# The live DGT DATEX II v3.6 feed URL.
_DGT_DATEX_URL = "https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v36.xml"


class DatexParser(BaseParser):
    """Parser for DATEX II SituationPublication XML from Spain's DGT.

    After calling :meth:`get_parsed_data`, the parsed alerts are stored
    internally and can be queried via :meth:`filter_by_road`,
    :meth:`filter_by_admin`, and :meth:`filter_by_location`.

    Args:
        downloader: HTTP downloader instance.  Defaults to ``None``.
        truck_only: When ``True`` (the default), alerts whose
            ``vehicleType`` is exclusively non-truck (e.g. ``bicycle``)
            are **excluded**.  Set to ``False`` to include everything.
    """

    def __init__(
        self, downloader: GenericDownloader | None = None, truck_only: bool = True
    ) -> None:
        super().__init__(downloader)
        self.truck_only = truck_only
        self._alerts: list[TruckDashboardAlert] = []

    @property
    def country(self) -> str:
        """Returns the two-letter country code for Spain."""
        return "ES"

    @property
    def alerts(self) -> list[TruckDashboardAlert]:
        """The most recently parsed list of alerts."""
        return self._alerts

    # ------------------------------------------------------------------
    # Core parsing
    # ------------------------------------------------------------------

    async def parse(self, raw_data: str) -> list[TruckDashboardAlert]:
        """Parse raw DATEX II XML into a list of alerts.

        Args:
            raw_data: The XML document as a UTF-8 string.

        Returns:
            A list of :class:`TruckDashboardAlert` instances.
        """
        root = etree.fromstring(raw_data.encode("utf-8"))  # noqa: S320
        nsmap = self._build_nsmap(root)
        alerts: list[TruckDashboardAlert] = []

        for situation in root.findall("sit:situation", nsmap):
            situation_id = situation.get("id", "")
            overall_severity = self._text(situation, "sit:overallSeverity", nsmap)

            for record in situation.findall("sit:situationRecord", nsmap):
                alert = self._parse_record(record, situation_id, overall_severity, nsmap)
                if self.truck_only and self._is_non_truck_only(alert):
                    continue
                alerts.append(alert)

        self._alerts = alerts
        print(f"Parsed {len(alerts)} DATEX II alerts.")
        return alerts

    async def get_parsed_data(
        self,
        output_file: str | Path | None = None,
        output_folder: str | Path | None = None,
    ) -> list[TruckDashboardAlert]:
        """Download, parse, and optionally save DATEX II alerts.

        Args:
            output_file: Explicit file path to save JSON output.
            output_folder: Folder — file will be named
                ``datex_alerts.json``.

        Returns:
            The list of parsed alerts.
        """
        raw_data = await self.downloader.download(_DGT_DATEX_URL)
        alerts = await self.parse(raw_data)

        if output_file:
            self.save_alerts(alerts, Path(output_file))
        elif output_folder:
            self.save_alerts(alerts, Path(output_folder) / "datex_alerts.json")

        return alerts

    # ------------------------------------------------------------------
    # Filtering (Phase 4)
    # ------------------------------------------------------------------

    def filter_by_road(self, road: str) -> list[TruckDashboardAlert]:
        """Return alerts whose ``road_name`` matches *road* (case-sensitive).

        Args:
            road: Road code to match exactly (e.g. ``"AP-7"``).

        Returns:
            Filtered list of alerts.
        """
        return [a for a in self._alerts if a.road_name and road == a.road_name]

    def filter_by_admin(
        self,
        community: str | None = None,
        province: str | None = None,
        municipality: str | None = None,
    ) -> list[TruckDashboardAlert]:
        """Return alerts matching administrative metadata (case-insensitive).

        Checks **both** ``location_from`` and ``location_to`` so that
        cross-province incidents are not missed.

        Args:
            community: Autonomous Community to match.
            province: Province to match.
            municipality: Municipality to match.

        Returns:
            Filtered list of alerts.
        """

        def _matches_point(point: LocationPoint | None) -> bool:
            if point is None:
                return False
            if community and (
                not point.community or community.lower() not in point.community.lower()
            ):
                return False
            if province and (
                not point.province or province.lower() not in point.province.lower()
            ):
                return False
            if municipality and (
                not point.municipality
                or municipality.lower() not in point.municipality.lower()
            ):
                return False
            return True

        return [
            a
            for a in self._alerts
            if _matches_point(a.location_from) or _matches_point(a.location_to)
        ]

    def filter_by_location(
        self, lat: float, lon: float, radius_km: float
    ) -> list[TruckDashboardAlert]:
        """Return alerts within *radius_km* of a GPS coordinate.

        Uses the Haversine formula.  Checks distance to **both**
        ``location_from`` and ``location_to`` coordinates.

        Args:
            lat: Latitude of the query center.
            lon: Longitude of the query center.
            radius_km: Maximum distance in kilometers.

        Returns:
            Filtered list of alerts.
        """

        def _within(point: LocationPoint | None) -> bool:
            if point is None or point.latitude is None or point.longitude is None:
                return False
            return haversine_km(lat, lon, point.latitude, point.longitude) <= radius_km

        return [
            a
            for a in self._alerts
            if _within(a.location_from) or _within(a.location_to)
        ]

    # Convenience alias from the plan's "Final Delivery Format"
    def get_alerts_near(
        self, lat: float, lon: float, radius: float
    ) -> list[TruckDashboardAlert]:
        """Alias for :meth:`filter_by_location`.

        Args:
            lat: Center latitude.
            lon: Center longitude.
            radius: Radius in kilometers.

        Returns:
            Alerts within the radius.
        """
        return self.filter_by_location(lat, lon, radius)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def save_alerts(alerts: list[TruckDashboardAlert], path: Path) -> None:
        """Serialize alerts to a JSON file.

        Args:
            alerts: The alert list to save.
            path: Destination file path.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [a.model_dump(mode="json") for a in alerts]
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Saved {len(alerts)} alerts → {path}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_nsmap(root: etree.ElementBase) -> dict[str, str]:
        """Build a prefix → URI namespace map from the XML root.

        Args:
            root: The lxml root element.

        Returns:
            Namespace dictionary suitable for ``findall`` / ``find``.
        """
        return {prefix: uri for prefix, uri in root.nsmap.items() if prefix is not None}

    @staticmethod
    def _text(
        element: etree.ElementBase,
        xpath: str,
        nsmap: dict[str, str],
    ) -> str | None:
        """Safe text extraction via XPath.

        Args:
            element: Parent element.
            xpath: XPath expression.
            nsmap: Namespace map.

        Returns:
            The text content, or ``None`` if the node is missing.
        """
        node = element.find(xpath, nsmap)
        return node.text if node is not None else None

    def _parse_record(
        self,
        record: etree.ElementBase,
        situation_id: str,
        overall_severity: str | None,
        nsmap: dict[str, str],
    ) -> TruckDashboardAlert:
        """Parse a single ``<sit:situationRecord>`` into a model.

        Args:
            record: The situationRecord XML element.
            situation_id: Parent situation ID.
            overall_severity: Severity from the parent situation.
            nsmap: Namespace map.

        Returns:
            A populated alert.
        """
        record_id = record.get("id", "")

        # --- Severity (record-level overrides situation-level) ---
        severity = self._text(record, "sit:severity", nsmap) or overall_severity

        # --- Timestamps ---
        creation_time = self._text(record, "sit:situationRecordCreationTime", nsmap)
        version_time = self._text(record, "sit:situationRecordVersionTime", nsmap)
        start_time = self._text(
            record,
            "sit:validity/com:validityTimeSpecification/com:overallStartTime",
            nsmap,
        )
        end_time = self._text(
            record,
            "sit:validity/com:validityTimeSpecification/com:overallEndTime",
            nsmap,
        )

        # --- Cause ---
        cause_type = self._text(record, "sit:cause/sit:causeType", nsmap)
        detailed_cause_type = self._text(
            record,
            "sit:cause/sit:detailedCauseType/sit:roadMaintenanceType",
            nsmap,
        )

        # --- Restriction ---
        management_type = self._text(
            record,
            "sit:roadOrCarriagewayOrLaneManagementType",
            nsmap,
        )
        vehicle_type = self._text(
            record,
            "sit:forVehiclesWithCharacteristicsOf/com:vehicleType",
            nsmap,
        )

        # --- Location reference ---
        loc_ref = record.find("sit:locationReference", nsmap)
        road_name: str | None = None
        road_destination: str | None = None
        direction: str | None = None
        carriageway: str | None = None
        lane_usage: str | None = None
        location_from: LocationPoint | None = None
        location_to: LocationPoint | None = None

        if loc_ref is not None:
            # Road info (shared across both location types)
            road_name = self._text(
                loc_ref,
                "loc:supplementaryPositionalDescription/loc:roadInformation/loc:roadName",
                nsmap,
            )
            road_destination = self._text(
                loc_ref,
                "loc:supplementaryPositionalDescription/loc:roadInformation/loc:roadDestination",
                nsmap,
            )
            carriageway = self._text(
                loc_ref,
                "loc:supplementaryPositionalDescription/loc:carriageway/loc:carriageway",
                nsmap,
            )
            lane_usage = self._text(
                loc_ref,
                "loc:supplementaryPositionalDescription/loc:carriageway/loc:lane/loc:laneUsage",
                nsmap,
            )

            # Branch on location type
            loc_type = loc_ref.get(f"{{{nsmap.get('xsi', '')}}}type", "")

            if "SingleRoadLinearLocation" in loc_type:
                location_from, location_to, direction = self._parse_linear_location(
                    loc_ref, nsmap
                )
            elif "PointLocation" in loc_type:
                location_from, direction = self._parse_point_location(loc_ref, nsmap)

        return TruckDashboardAlert(
            situation_id=situation_id,
            record_id=record_id,
            creation_time=creation_time,
            version_time=version_time,
            severity=severity,
            start_time=start_time,
            end_time=end_time,
            management_type=management_type,
            vehicle_type=vehicle_type,
            cause_type=cause_type,
            detailed_cause_type=detailed_cause_type,
            road_name=road_name,
            road_destination=road_destination,
            direction=direction,
            carriageway=carriageway,
            lane_usage=lane_usage,
            location_from=location_from,
            location_to=location_to,
        )

    def _parse_tpeg_point(
        self, point_el: etree.ElementBase, nsmap: dict[str, str]
    ) -> LocationPoint:
        """Extract a LocationPoint from a TpegNonJunctionPoint element.

        Args:
            point_el: The ``<loc:from>``, ``<loc:to>``, or ``<loc:point>``
                element.
            nsmap: Namespace map.

        Returns:
            Populated LocationPoint.
        """
        lat = self._text(point_el, "loc:pointCoordinates/loc:latitude", nsmap)
        lon = self._text(point_el, "loc:pointCoordinates/loc:longitude", nsmap)

        ext_path = "loc:_tpegNonJunctionPointExtension/loc:extendedTpegNonJunctionPoint"
        km = self._text(point_el, f"{ext_path}/lse:kilometerPoint", nsmap)
        community = self._text(point_el, f"{ext_path}/lse:autonomousCommunity", nsmap)
        province = self._text(point_el, f"{ext_path}/lse:province", nsmap)
        municipality = self._text(point_el, f"{ext_path}/lse:municipality", nsmap)

        return LocationPoint(
            latitude=float(lat) if lat else None,
            longitude=float(lon) if lon else None,
            km_point=float(km) if km else None,
            community=community,
            province=province,
            municipality=municipality,
        )

    def _parse_linear_location(
        self, loc_ref: etree.ElementBase, nsmap: dict[str, str]
    ) -> tuple[LocationPoint | None, LocationPoint | None, str | None]:
        """Parse a ``SingleRoadLinearLocation`` into from/to points.

        Args:
            loc_ref: The ``<sit:locationReference>`` element.
            nsmap: Namespace map.

        Returns:
            Tuple of ``(location_from, location_to, direction)``.
        """
        linear = loc_ref.find("loc:tpegLinearLocation", nsmap)
        if linear is None:
            return None, None, None

        from_el = linear.find("loc:from", nsmap)
        to_el = linear.find("loc:to", nsmap)

        location_from = (
            self._parse_tpeg_point(from_el, nsmap) if from_el is not None else None
        )
        location_to = (
            self._parse_tpeg_point(to_el, nsmap) if to_el is not None else None
        )

        direction = self._text(
            linear,
            "loc:_tpegLinearLocationExtension/loc:extendedTpegLinearLocation/lse:tpegDirectionRoad",
            nsmap,
        )
        return location_from, location_to, direction

    def _parse_point_location(
        self, loc_ref: etree.ElementBase, nsmap: dict[str, str]
    ) -> tuple[LocationPoint | None, str | None]:
        """Parse a ``PointLocation`` into a single point.

        Args:
            loc_ref: The ``<sit:locationReference>`` element.
            nsmap: Namespace map.

        Returns:
            Tuple of ``(location_from, direction)``.
        """
        point_loc = loc_ref.find("loc:tpegPointLocation", nsmap)
        if point_loc is None:
            return None, None

        point_el = point_loc.find("loc:point", nsmap)
        location = (
            self._parse_tpeg_point(point_el, nsmap) if point_el is not None else None
        )

        direction = self._text(
            point_loc,
            "loc:_tpegSimplePointExtension/loc:extendedTpegSimplePoint/lse:tpegDirectionRoad",
            nsmap,
        )
        return location, direction

    @staticmethod
    def _is_non_truck_only(alert: TruckDashboardAlert) -> bool:
        """Check if an alert's vehicle type is exclusively non-truck.

        Args:
            alert: The alert to check.

        Returns:
            ``True`` if the alert is irrelevant to trucks.
        """
        if not alert.vehicle_type:
            return False
        return alert.vehicle_type.lower() in NON_TRUCK_VEHICLE_TYPES
