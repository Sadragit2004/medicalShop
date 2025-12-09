from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class AttributeServiceInterface(ABC):

    @abstractmethod
    def create_attribute(self, data: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    def update_attribute(self, attribute_id: int, data: Dict[str, Any]) -> Optional[Any]:
        pass

    @abstractmethod
    def delete_attribute(self, attribute_id: int) -> bool:
        pass

    @abstractmethod
    def get_attribute_by_id(self, attribute_id: int) -> Optional[Any]:
        pass

    @abstractmethod
    def get_all_attributes(self) -> List[Any]:
        pass

    @abstractmethod
    def set_product_attribute_value(self, product_id: int, attribute_id: int, value: Any) -> Any:
        pass

    @abstractmethod
    def get_product_attributes(self, product_id: int) -> List[Dict[str, Any]]:
        pass