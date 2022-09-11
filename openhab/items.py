class OhItem:
    def __init__(self, status):
        self.status = status
        
    def should_update(self, new_value):
        return self.status == new_value
        
class RollerShutter(OhItem):
    def __init__(self, status):
        super().__init__(status)
        
    def is_open(self):
        return self.status == 0
    
    def is_closed(self):
        return self.status == 100
