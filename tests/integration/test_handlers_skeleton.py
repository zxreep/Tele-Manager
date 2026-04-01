"""Integration-test skeletons for handlers with mocked Telegram API."""


class FakeTelegramAPI:
    def send_message(self, chat_id: int, text: str) -> None:
        self.last_message = (chat_id, text)


def test_handler_flow_placeholder() -> None:
    """Replace with a handler integration flow using FakeTelegramAPI."""
    api = FakeTelegramAPI()
    api.send_message(123, "hello")
    assert api.last_message == (123, "hello")
