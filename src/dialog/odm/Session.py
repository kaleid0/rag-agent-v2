from pymongo import ASCENDING, DESCENDING

# from src.memory import ShortTermMemory
from src.dialog.DialogMessage import DialogMessage
from src.database import BaseDocument

# from ...llm.Message import Messages


class Session(BaseDocument):
    user_id: str | None = None
    metadata: dict = {}
    message_count: int = 0  # 消息计数器
    last_summary_count: int = 0  # 上次总结时的消息数
    dialog_messages: list[DialogMessage] = []
    # shot_term_memory: ShortTermMemory | None = None

    class Settings:
        name = "session"  # MongoDB 集合名
        # 定义索引列表
        indexes = [
            # 复合索引：(user_id 升序, created_at 降序)
            # 1 代表升序 (ASCENDING)，-1 代表降序 (DESCENDING)
            [("user_id", ASCENDING), ("created_at", DESCENDING)],
            # user_id 上的单键索引
            "user_id",
        ]
        use_state_management = True

    def get_history(
        self,
        limit: int | None = None,
        start_rev_index: int | None = None,
        end_rev_index: int | None = None,
    ) -> list[dict[str, str]]:
        msgs = self.messages
        length = len(msgs)
        if limit:
            return msgs[-limit:]

        start_rev_index = start_rev_index or 0
        end_rev_index = end_rev_index or length
        if (
            end_rev_index <= start_rev_index
            or end_rev_index <= 0
            or start_rev_index <= 0
        ):
            raise ValueError(
                "错误: 参数设置无效。请确保 end_rev_index > start_rev_index 且两者都大于 0。"
            )
        if length < end_rev_index:
            raise ValueError(
                f"警告: 数组长度 ({length}) 小于 {end_rev_index}，无法安全提取。"
            )

        slice_start_index = -end_rev_index

        # 2. 切片的结束负索引（不包含）
        # 要包含倒数第 start_rev_index 个元素，切片的结束点必须是其负索引加 1
        slice_end_index = -start_rev_index + 1

        # 执行切片操作
        return msgs[slice_start_index:slice_end_index]

    def get_all_user_messages(self) -> list[dict[str, str]]:
        return [
            msg.message for msg in self.dialog_messages if msg.message.role == "user"  # type: ignore
        ]

    def add_message(self, message: DialogMessage) -> None:
        self.dialog_messages.append(message)
        # self.updated_at = datetime.now()

    @property
    def messages(self) -> list[dict[str, str]]:
        return [msg.message for msg in self.dialog_messages]


# 保存和加载由 ODM 自动完成
# s = Session(user_id="u1", messages=[Message(role=RoleEnum.user, content="hi")])
# await s.insert()
# loaded = await Session.get(s.id)
# print(loaded.dict())
