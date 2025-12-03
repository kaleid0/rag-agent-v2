from langchain_text_splitters import RecursiveCharacterTextSplitter as RCTSplitter


class RecursiveCharacterTextSplitter:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.splitter = RCTSplitter()

    def split_text(self, text: str) -> list[dict[str, str]]:
        splitted_texts = self.splitter.split_text(text)
        return [{"content": t} for t in splitted_texts]
