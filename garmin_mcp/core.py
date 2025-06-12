import datetime
import urllib.parse
from typing import List, Dict, Any, Optional
import garth
from mcp.server.fastmcp import FastMCP
from garth import Client


def create_mcp_server(client: Client, **settings) -> FastMCP:
    fast_mcp = FastMCP(
        name="garmin-mcp",
        **settings,
    )

    @fast_mcp.tool()
    def get_current_date() -> str:
        """
        Get the current date for Garmin Connect API usage.
        
        Returns:
            Current date in YYYY-MM-DD format
        """
        return datetime.datetime.now().strftime("%Y-%m-%d")

    @fast_mcp.tool()
    def get_activities(
            start_date: str,
            limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get activities from Garmin Connect.

        :param start_date: Start date in YYYY-MM-DD format.
        :param limit: Maximum number of activities to return (default: 20).
        :return: Dictionary containing activity data.
        """
        params = {
            "startDate": start_date,
            "limit": limit
        }
        endpoint = f"activitylist-service/activities/search/activities?{urllib.parse.urlencode(params)}"
        return client.connectapi(endpoint)

    @fast_mcp.tool()
    def get_activity_details(activity_id: str) -> Dict[str, Any]:
        """
        Get details of a specific activity from Garmin Connect.

        :param activity_id: The ID of the activity.
        :return: Dictionary containing detailed activity data.
        """
        return client.connectapi(f"activity-service/activity/{activity_id}")

    @fast_mcp.tool()
    def get_heart_rate_list(start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Get heart rate overview for that range from Garmin Connect.
        
        :param start_date: Start date in YYYY-MM-DD format.
        :param end_date: End date in YYYY-MM-DD format.
        :return: Dictionary containing heart rate data within the specified date range.
        """
        return client.connectapi(f"usersummary-service/stats/heartRate/daily/{start_date}/{end_date}")

    @fast_mcp.tool()
    def get_heart_rate_details(date: str, time_start: str=None, time_end: str=None, interval_minutes: int = 10):

        """
        Get heart rate details for a specific day from Garmin Connect.
        This interval_minutes is to filter the heart rate data to avoid too many entries.
        The original data is logged every 2 minutes, so using 10 minutes will give you 5 entries per hour.
        Empty values are skipped. If entries are missing, heart rate was not logged at that time. Time is rounded to the nearest interval.

        :param date: Date in YYYY-MM-DD format.
        :param interval_minutes: Interval in minutes to filter heart rate data (default: 10).
        :param time_start: Start time in HH:MM:SS format (optional). Both time_start and time_end must be provided or neither.
        :param time_end: End time in HH:MM:SS format (optional). Both both time_start and time_end must be provided or neither.
        :return: Dictionary containing detailed heart rate data for the given day.
        """
        if bool(time_start) != bool(time_end):
            raise ValueError("Both time_start and time_end must be provided or neither.")

        # Parse start and end times if provided
        start_time_obj = datetime.datetime.strptime(time_start, "%H:%M:%S").time() if time_start else None
        end_time_obj = datetime.datetime.strptime(time_end, "%H:%M:%S").time() if time_end else None

        data = client.connectapi(f"wellness-service/wellness/dailyHeartRate?date={date}")
        heart_rate_values = data.pop("heartRateValues", [])
        data["heartRateValues"] = []

        last_logged_time = None

        for hr in heart_rate_values:
            if hr[1] is None:
                continue

            time_hr = datetime.datetime.fromtimestamp(float(hr[0]) / 1000)
            time_only = time_hr.time()

            if start_time_obj and end_time_obj:
                if not (start_time_obj <= time_only <= end_time_obj):
                    continue

            if last_logged_time is None or (time_hr - last_logged_time).total_seconds() >= interval_minutes * 60:
                data["heartRateValues"].append({
                    "time": time_hr.strftime("%H:%M:%S"),
                    "value": hr[1]
                })
                last_logged_time = time_hr

        return data

    @fast_mcp.tool()
    def get_heart_rate_zones():
        """
        Get heart rate zones from Garmin Connect.

        :return: Dictionary containing heart rate zone data.
        """
        return client.connectapi("biometric-service/heartRateZones/")

    @fast_mcp.tool()
    def get_sleep_data(
            end_date: Optional[str] = None,
            nights: int = 1,
            include_movement: bool = False
    ) -> List[garth.SleepData]:
        """
        Get sleep stats for a given date and number of nights from Garmin Connect.
        
        :param end_date: End date for sleep data (YYYY-MM-DD). If None, uses current date.
        :param nights: Number of nights to retrieve (default: 1).
        :param include_movement: Whether to include detailed sleep movement data.
        :return: List of sleep data objects.
        """
        sleep_data = garth.SleepData.list(end_date, nights, client=client)
        if not include_movement:
            for night in sleep_data:
                if hasattr(night, "sleep_movement"):
                    delattr(night, "sleep_movement")
        return sleep_data

    @fast_mcp.tool()
    def get_daily_stress(
            end_date: Optional[str] = None,
            days: int = 1
    ) -> List[garth.DailyStress]:
        """
        Get daily stress data for a given date and number of days from Garmin Connect.
        
        :param end_date: End date for stress data (YYYY-MM-DD). If None, uses current date.
        :param days: Number of days to retrieve (default: 1).
        :return: List of daily stress data objects.
        """
        return garth.DailyStress.list(end_date, days, client=client)

    @fast_mcp.tool()
    def get_weekly_stress(
            end_date: Optional[str] = None,
            weeks: int = 1
    ) -> List[garth.WeeklyStress]:
        """
        Get weekly stress data for a given date and number of weeks from Garmin Connect.
        
        :param end_date: End date for stress data (YYYY-MM-DD). If None, uses current date.
        :param weeks: Number of weeks to retrieve (default: 1).
        :return: List of weekly stress data objects.
        """
        return garth.WeeklyStress.list(end_date, weeks, client=client)

    @fast_mcp.tool()
    def get_daily_intensity_minutes(
            end_date: Optional[str] = None,
            days: int = 1
    ) -> List[garth.DailyIntensityMinutes]:
        """
        Get daily intensity minutes data for a given date and number of days from Garmin Connect.
        
        :param end_date: End date for intensity data (YYYY-MM-DD). If None, uses current date.
        :param days: Number of days to retrieve (default: 1).
        :return: List of daily intensity minutes data objects.
        """
        return garth.DailyIntensityMinutes.list(end_date, days, client=client)

    return fast_mcp
