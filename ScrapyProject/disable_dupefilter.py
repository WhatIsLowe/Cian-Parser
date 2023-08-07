from scrapy.dupefilters import RFPDupeFilter


class DisableDuplicatesFilter(RFPDupeFilter):
    def request_seen(self, request) -> bool:
        return False
