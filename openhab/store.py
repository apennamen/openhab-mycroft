from rapidfuzz import fuzz


class OpenHabItemStore:
    """Holds the items found in OpenHab.
    Acts as a cache and provides utility methods
    to search for items based on user requests.
    """

    def __init__(self, json_response):
        self.items = dict()

        for tag in self.supported_tags():
            self.items[tag] = dict()

        for x in range(0, len(json_response)):
            for tag in self.supported_tags():
                if (tag in json_response[x]['tags']):
                    self.items[tag].update(
                        {json_response[x]['name']: json_response[x]['label']})
                else:
                    pass

    def supported_tags(self):
        return ["Shutter", "TemperatureSensor"]

    def print_items(self):
        if self.items_count() == 0:
            return ""

        result = ""
        for item_type in self.items.keys():
            result += "%s: %s." % (item_type, ', '.join(list(self.items[item_type].values())))
        
        return result

    def items_count(self):
        count = 0
        for item_type in self.items.keys():
            count += len(self.items[item_type])
        return count

    def find_item(self, message_item):
        """Find item name  in OpenHab that matches provided item in user request."""
        best_score = 0
        score = 0
        best_item = (None, None)

        for item_type in self.items.keys():
            for item_name, item_label in list(self.items[item_type].items()):
                score = fuzz.ratio(message_item, item_label,
                                    score_cutoff=best_score)
                if score > best_score:
                    best_score = score
                    best_item = (item_name, item_type)

        return best_item

    def find_item_of_type(self, message_item, item_type):
        """Find item name  in OpenHab that matches provided item in user request.
        Only looks for item tagged with label `item_type` in OpenHab
        """
        if item_type not in self.items:
            return (None, item_type)
        
        best_score = 0
        score = 0
        best_item = (None, item_type)
        
        for item_name, item_label in list(self.items[item_type].items()):
            score = fuzz.ratio(message_item, item_label,
                                score_cutoff=best_score)
            if score > best_score:
                best_score = score
                best_item = (item_name, item_type)

        return best_item
