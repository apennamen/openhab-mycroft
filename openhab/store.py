from rapidfuzz import fuzz


class OpenHabItemStore:
    """Holds the items found in OpenHab.
    Acts as a cache and provides utility methods
    to search for items based on user requests.
    """
    def __init__(self):
        self.items = dict()

        for tag in self.supported_tags():
            self.items[tag] = dict()

    def supported_tags(self):
        return ["Shutter"]

    def print_items(self):
        if self.items_count() == 0:
            return ""

        for item_type in self.items.keys():
            return "%s: %s" % (item_type, ', '.join(list(self.items[item_type].values())))

    def items_count(self):
        count = 0
        for item_type in self.items.keys():
            count += len(self.items[item_type])
        return count

    def find_item_name_and_type(self, message_item):
        """Find item name  in OpenHab that matches provided item in user request."""
        best_score = 0
        score = 0
        best_item = (None, None)

        try:
            for item_type in self.items.keys():
                for item_name, item_label in list(self.items[item_type].items()):
                    score = fuzz.ratio(message_item, item_label,
                                       score_cutoff=best_score)
                    if score > best_score:
                        best_score = score
                        best_item = (item_name, item_type)
        except KeyError:
            pass

        return best_item

    def find_item_name(self, message_item, item_type):
        """Find item name  in OpenHab that matches provided item in user request.
        Only looks for item tagged with label `item_type` in OpenHab
        """
        best_score = 0
        score = 0
        best_item = None

        try:
            for item_name, item_label in list(self.items[item_type].items()):
                score = fuzz.ratio(message_item, item_label,
                                   score_cutoff=best_score)
                if score > best_score:
                    best_score = score
                    best_item = item_name
        except KeyError:
            pass

        return best_item
