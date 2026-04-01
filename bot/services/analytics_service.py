class AnalyticsService:
    async def get_snapshot(self) -> dict:
        return {
            "daily_active_users": 0,
            "messages_processed": 0,
        }
