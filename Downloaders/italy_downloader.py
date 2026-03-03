import winloop
import asyncio
from config import CONSTANTS
from Downloaders.base_downloader import BaseDownloader


class ItalyDownloader(BaseDownloader):
    """
    Downloader for Italian highway camera data from multiple sources.
    """

    async def get_autostrade_raw(self) -> str | None:
        """
        Fetches raw data from the main Autostrade service.

        Returns:
            str | None: The raw JSON string or None if failed.
        """
        url: str = CONSTANTS.ITALY.BASE_URL
        try:
            return await self.download(url=url)
        except Exception as e:
            print(f"Error downloading Autostrade data: {e}")
            return None

    async def get_a22_raw(self) -> str | None:
        """
        Fetches raw data for the A22 highway by extracting the JSON injected into HTML.

        Returns:
            str | None: The extracted raw JSON string or None if failed.
        """
        url: str = CONSTANTS.ITALY.A22.BASE_URL
        keyword_start: str = CONSTANTS.ITALY.A22.CAMERA_KEYWORDS[0]
        keyword_end: str = CONSTANTS.ITALY.A22.CAMERA_KEYWORDS[1]
        try:
            html_result: str = await self.download(url)
            start_index: int = html_result.find(keyword_start)
            end_index: int = html_result.find(keyword_end)

            if start_index == -1 or end_index == -1:
                return None

            json_str: str = html_result[
                start_index + len(keyword_start) : end_index
            ].strip()
        except Exception as e:
            print(f"Error downloading A22 data: {e}")
            return None
        else:
            return json_str

    async def get_a4_abp_raw(self) -> str | None:
        """
        Fetches raw data from the A4 ABP section.

        Returns:
            str | None: The raw JSON string or None if failed.
        """
        url: str = CONSTANTS.ITALY.A4.ABP.CAMERA_API
        try:
            return await self.download(url)
        except Exception as e:
            print(f"Error downloading A4 ABP data: {e}")
            return None

    async def get_a4_cav_raw(self) -> str | None:
        """
        Fetches raw data from the A4 CAV section.

        Returns:
            str | None: The raw JSON string or None if failed.
        """
        url: str = CONSTANTS.ITALY.A4.CAV.CAMERA_API
        try:
            return await self.download(url)
        except Exception as e:
            print(f"Error downloading A4 CAV data: {e}")
            return None

    async def get_a4_satap_raw(self) -> str | None:
        """
        Fetches raw HTML data from the A4 SATAP section.

        Returns:
            str | None: The raw HTML string or None if failed.
        """
        url: str = CONSTANTS.ITALY.A4.SATAP.BASE_URL
        try:
            return await self.download(url)
        except Exception as e:
            print(f"Error downloading A4 SATAP data: {e}")
            return None

    async def get_data(self) -> dict[str, str | None]:
        """
        Downloads raw data from all Italian providers concurrently.

        Returns:
            dict[str, str | None]: A dictionary mapping provider names to their raw data.
        """
        results = await asyncio.gather(
            self.get_autostrade_raw(),
            self.get_a22_raw(),
            self.get_a4_abp_raw(),
            self.get_a4_cav_raw(),
            self.get_a4_satap_raw(),
        )

        return {
            "autostrade": results[0],
            "a22": results[1],
            "a4_abp": results[2],
            "a4_cav": results[3],
            "a4_satap": results[4],
        }


if __name__ == "__main__":
    downloader = ItalyDownloader()
    data = winloop.run(downloader.get_data())
    print(f"Downloaded data keys: {list(data.keys())}")
