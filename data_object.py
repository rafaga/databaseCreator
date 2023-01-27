

class GenericEntity():
    __entity_id = 0
    __entity_catalog = {}

    @property
    def id(self):
        """
        Property to get Star GroupID
        """
        return self.__entity_id

    @id.setter
    def id(self, value):
        """
        Property to set Star GroupID
        """
        if isinstance(value,int):
            self.__entity_id = value

    @property
    def entity_type(self):
        return self.__entity_catalog

    @entity_type.setter
    def entity_type(self, value):
        self.__entity_catalog = value