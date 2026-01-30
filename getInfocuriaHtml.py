import requests
import json
from playwright.sync_api import Page, expect, Playwright, sync_playwright, Frame
url = r"https://infocuria.curia.europa.eu/tabs/jurisprudence?lang=EN&typedoc=POSITION"

url = r"https://infocuriaws.curia.europa.eu/elastic-connector/search"


# construct the document url from the attributes
def constructUrl(content_item, doc_type_code, doc_base_url, logic_doc_id):
    parts = []
    parts.append(doc_base_url)
    parts.append(content_item["id"].split("/")[0])

    parts.append("/")

    # This assumes the date is after 2000, !!!! (Can it be earlier? how is it detected?)
    parts.append("20"+content_item["id"].split("/")[2])
    parts.append("/")
    parts.append(content_item["idProcedure"].replace("/", "-"))

    parts.append("/")
    parts.append(doc_type_code)

    parts.append("/")
    parts.append(logic_doc_id.split("_")[1])
    parts.append("-")
    parts.append(content_item["docLang"])
    parts.append("-")

    # What is this number ??????????
    parts.append("1-")

    # there might be pdfs and html documents assuming the ui on the website is showing everything

    assert("html" in [docFormat.lower() for docFormat in content_item["formats"]]) # make sure html is available
    parts.append("html")
    return "".join(parts)


def downloadDocument(url):
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    chrome_options = Options()
    chrome_options.page_load_strategy = 'normal'
    # chrome_options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=chrome_options)
    # WebDriverWait(driver, 10).until()

    driver.get(url)
    
    import time
    time.sleep(5)
    iframe = driver.find_element(By.ID, "document-inner-frame")
    driver.switch_to.frame(iframe)

    with open('page.html', 'w+', encoding="utf-8") as f:
        f.write(driver.page_source)
    print(driver.content)

    driver.quit()


def getUrls(year, month):

    last_day = str(datetime.date(year, month, calendar.monthrange(year, month)[1]))
    first_day = str(datetime.date(year, month, 1))

    print(first_day, last_day)
    
    # exit()
    

    dateRange = {"field": "docDate", "values": [first_day, last_day],
                     "valuesWithFullHierarchy": [first_day, last_day]}
    
    print(dateRange)

    query = {
    "searchTerm": "", "multiSearchTerms": [],
    "sortTermList": [{"sortDirection": "DESC", "sortTerm": "DOC_DATE"}],
    "pagination": {"pageNumber": 0, "pageSize": 100, "from": 1, "to": 100},
    "language": "DE", "tabName": "jurisprudence", "isAllTabsRequest": "false",
    "ecli": "", "publishedId": "", "usualName": "", "logicDocId": "",
    "filtersValue": [],
    "isSearchExact": "true", "searchSources": ["document", "metadata"]}

    query["filtersValue"].append(dateRange)

    doc_base_url = r"https://infocuria.curia.europa.eu/tabs/document/"
    url = r"https://infocuriaws.curia.europa.eu/elastic-connector/search"

    
    search_results = []
    
    response = requests.post(url, json=query)
    objectified = json.loads(response.content)

    # print(type(objectified["searchHits"]))
    # print(objectified["searchHits"])
    # exit()
    search_results = search_results + objectified["searchHits"]
    # get additional pages of results
    # print(objectified["totalHits"])
    if additional_pages := int(objectified["totalHits"]/100):
        for i in range(additional_pages):
            query["pagination"]["pageNumber"] = query["pagination"]["pageNumber"] + 1
            query["pagination"]["from"] = query["pagination"]["from"] + query["pagination"]["pageSize"]
            query["pagination"]["to"] = query["pagination"]["to"] + query["pagination"]["pageSize"]
            response = requests.post(url, json=query)
            objectified = json.loads(response.content)
            search_results = search_results + objectified["searchHits"]
    

    urls = []
    # format_string = t"{doc_base_url}/{category}/{year}/{procedure_url}/{document_type}/{doc_id}-{doc_lang}-{doc_format}"

    for item in search_results:
        doc_type_code = item["content"]["docTypeCode"]
        logic_doc_id = item["content"]["logicDocId"]

        # try to get german language document
        filteredItems=list(filter(lambda ci: ci["docLang"]=="DE", item["content"]["groupByLogicalId"]))
        if len(filteredItems)==0:  # if no german document exists get english one
            filteredItems=list(filter(lambda ci: ci["docLang"]=="EN", item["content"]["groupByLogicalId"]))
        if len(filteredItems)==0:
            # no german or english documents -> skip this document
            continue

        assert(len(filteredItems) == 1)
        
        url = constructUrl(filteredItems[0], doc_type_code, doc_base_url, logic_doc_id)
        urls.append(url)
    print("got {} of {} document urls".format(len(urls), len(search_results)))
    return urls

def dump_frame_tree(frame, indent):
    print(indent + frame.name + '@' + frame.url)
    for child in frame.child_frames:
        dump_frame_tree(child, indent + "    ")

def downloadDocumentPlaywright(url):
    file_name = url.split("/")[-1]
    with sync_playwright() as pw:
        firefox = pw.firefox
        browser = firefox.launch()
        page = browser.new_page()

        page.goto(url)

        frame = page.frame("document-inner-frame")
        # print(frame)
        with open('{}.html'.format(file_name), 'w+', encoding="utf-8") as f:
            f.write(frame.content())
        # dispose context once it is no longer needed.
        browser.close()

if __name__ == "__main__":
    import sys
    import calendar
    import datetime

    # get month + year
    # save all documents into html files

    # print(sys.argv)

    if not len(sys.argv) == 5:
        print("Usage: python getInfocuriaHtml.py --year yyyy --month mm")
        exit()
    
    year = int(sys.argv[2])
    month = int(sys.argv[4])
    if not ( year > 1900 and year < 3000 and month > 0 and month <=12):
        print("Usage: python program --year yyyy --month mm")
    
    # exit()
    urls = getUrls(year, month)
    # [print(url) for url in urls]
    # exit()

    # testUrl = r"https://infocuria.curia.europa.eu/tabs/document/T/2025/T-0071-25-00000000PI-01-P-01/ARRET_NP/314514-EN-1-html"
    # # downloadDocument(testUrl)
    # downloadDocumentPlaywright(testUrl)
    # exit()
    for url in urls:
        downloadDocumentPlaywright(url)

