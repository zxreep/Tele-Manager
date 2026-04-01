class GroupService:
    async def get_group_summary(self, chat_id: int) -> dict:
        return {
            "chat_id": chat_id,
            "members": 0,
            "active_today": 0,
        }
