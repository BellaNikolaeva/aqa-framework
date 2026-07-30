from clients.base_client import BaseClient


class TagsClient(BaseClient):
    def list(self, search: str = None):
        params = {"search": search} if search else {}
        return self.get("/api/tags/", params=params)

    def create(self, name: str):
        return self.post("/api/tags/", json={"name": name})

    def get_by_id(self, tag_id: int):
        return self.get(f"/api/tags/{tag_id}/")

    def update(self, tag_id: int, name: str):
        return self.put(f"/api/tags/{tag_id}/", json={"name": name})

    def remove(self, tag_id: int):
        return super().delete(f"/api/tags/{tag_id}/")
