import winloop

from config import CONSTANTS
from Downloaders.base_downloader import BaseDownloader

CAMERA_BASE_URL: str = CONSTANTS.UK.CAMERA_URL
CAMERA_API: str = CONSTANTS.UK.CAMERA_API_URL


class UKDownloader(BaseDownloader):
    """
    Downloader for UK highway camera data (Traffic England).
    """

    async def get_data(self) -> str:
        """
        Downloads raw camera data for the UK.

        Returns:
            str: The raw JSON string from the UK API.
        """
        download_link: str = CAMERA_API
        return await self.download(download_link)


if __name__ == "__main__":
    downloader = UKDownloader()
    winloop.run(downloader.get_data())
