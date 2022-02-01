import unittest
import requests

from httmock import urlmatch, HTTMock

from db import db
import xxviii_dayslater as d2l


@urlmatch(netloc=r'(.*)')
def mock_section(url, request):
    with open("tests/28dl_section.html") as fp:
        read_data = fp.read()
    return read_data


@urlmatch(netloc=r'(.*)')
def mock_section_err(url, request):
    with open("tests/28dl_error.html") as fp:
        read_data = fp.read()
    return {
        "status_code": 404,
        "content": read_data
    }




class Test_d2l(unittest.TestCase):
    def _get(self):
        with HTTMock(mock_section):
            return self.x.crawl_section('leads-rumours-and-news.57/', 189)



    def setUp(self) -> None:
        db.connect(":memory:")
        self.x = d2l.xxviii_dayslater()
        self.url = 'https://www.28dayslater.co.uk/forum/leads-rumours-and-news.57/page-189?order=post_date&direction=desc'
        return

    
    def test_404(self) -> None:
        """Section HTTP 404"""
        
        with HTTMock(mock_section_err):
            res = self.x.get_section_page(self.url)
        self.assertDictEqual(res, {'status_code':404}, "Should return \"{'status_code':404}\"")
        return


    def test_sect_returns(self) -> None:
        """Section page meta"""

        with HTTMock(mock_section):
            res = self.x.get_section_page(self.url)
        self.assertEqual(res["status_code"], 200)
        self.assertEqual(res["max_pages"], 215)
        self.assertEqual(len(res["data"]), 10)
        return


    def test_sect_data(self) -> None:
        """Section Page Data"""

        with HTTMock(mock_section):
            res = self.x.get_section_page(self.url)

        for x in res["data"]:
            #[thread_url, title, crawl_date, thread_date]
            self.assertIs(type(x), list)
            self.assertEqual(len(x), 4)



    def test_crawl(self):
    
        self.assertEqual(self._get()[0], 10)#expect 10 inserts
        self.assertEqual(self._get()[0], 0)#expect 0 inserts due to dupes

        db.get_cur().execute("SELECT count(*) as count FROM refs").rowcount
        ex = db.get_cur().fetchone()

        self.assertEqual(ex["count"], 10)


    def test_crawl_change(self):
        #change 1 refs entry to have a diff place_id, and see if crawl_section inserts
        self._get()

        #only one set to have place_id of 1
        db.get_cur().execute("UPDATE refs SET place_id = 1 WHERE row_id = 1").rowcount
        db.get_cur().execute("COMMIT")

        #try and add another one with the same url
        x = self._get()
        db.get_cur().execute("SELECT count(*) as count FROM refs WHERE url = (SELECT url FROM refs WHERE place_id = 1)")

        #ensure there is only one entry for the url
        self.assertEqual(db.get_cur().fetchone()["count"], 1)

        return


    def test_crawl_404(self):
        with HTTMock(mock_section_err):
            res = self.x.crawl_section('leads-rumours-and-news.57/', 189)
        self.assertEqual(res[0], 0)



if __name__ == '__main__':
    unittest.main(verbosity=2)