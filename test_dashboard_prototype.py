"""Static structural checks for the standalone mobile-first BAM UI prototype.

These tests don't replace browser accessibility or end-to-end tests.
"""
from html.parser import HTMLParser
from pathlib import Path
import unittest

FILE=Path(__file__).parent/'ui'/'bam_dashboard_prototype.html'

class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=set()
        self.tags=[]
    def handle_starttag(self,tag,attrs):
        self.tags.append(tag)
        for key,value in attrs:
            if key=='id':
                if value in self.ids:
                    raise AssertionError('Duplicate HTML id: '+value)
                self.ids.add(value)

class DashboardPrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=FILE.read_text(encoding='utf-8')
        cls.parsed=Tags()
        cls.parsed.feed(cls.html)

    def test_required_landmarks_and_navigation(self):
        self.assertIn('main',self.parsed.tags)
        self.assertIn('nav',self.parsed.tags)
        self.assertIn('business',self.parsed.ids)
        self.assertIn('view',self.parsed.ids)
        self.assertIn('bottomNav',self.parsed.ids)

    def test_business_isolation_in_client_state(self):
        self.assertIn("state.drafts[state.business]",self.html)
        self.assertIn("state.business=event.target.value",self.html)
        self.assertIn("state.filter='all'",self.html)

    def test_drilldown_sections(self):
        for section in ['renderHome','renderContent','renderDraft',
                        'renderCalendar','renderAnalytics','renderConnections']:
            self.assertIn('function '+section+'(',self.html)

    def test_no_live_network_or_publication(self):
        for forbidden in ['fetch(', 'XMLHttpRequest', 'localStorage',
                          'sessionStorage', 'document.cookie', 'publishPost(']:
            self.assertNotIn(forbidden,self.html)
        self.assertIn('Nothing publishes',self.html)
        self.assertIn('Sample data only',self.html)

    def test_accessibility_basics(self):
        self.assertIn('name="viewport"',self.html)
        self.assertIn('aria-label="Main navigation"',self.html)
        self.assertIn('aria-live="polite"',self.html)
        self.assertIn('prefers-reduced-motion',self.html)

if __name__=='__main__':unittest.main()
