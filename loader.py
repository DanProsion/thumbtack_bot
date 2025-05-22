from keyboard.mkb import MarkupKeyboard

mkb = MarkupKeyboard()

class init_objects:
    driver = None
    thumbtack_register = None
    company_search_flow = None
    project_creation_handler = None

    @classmethod
    def init(cls):
        from automation.browser import get_driver
        from automation.register import ThumbtackRegister
        from automation.review import ProjectCreationHandler
        from automation.search_companies import CompanySearchFlow

        cls.driver = get_driver()
        cls.thumbtack_register = ThumbtackRegister(cls.driver)
        cls.company_search_flow = CompanySearchFlow(cls.driver)
        cls.project_creation_handler = ProjectCreationHandler(cls.driver)






