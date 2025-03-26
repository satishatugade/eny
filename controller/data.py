from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv
from selenium.common.exceptions import StaleElementReferenceException
import pytesseract
import pandas as pd
# from datetime import datetime
# from selenium.common.exceptions import TimeoutException
import psycopg2
import time
import os
from PIL import Image



def load_database_config():
    load_dotenv()
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'username': os.getenv('DB_USERNAME', 'postgres'),
        'password': os.getenv('DB_PASSWORD', '123456789'),
        'dbname': os.getenv('DB_NAME', 'eny_data')
    }

def database_connection():
    config = load_database_config()
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            user=config['username'],
            password=config['password'],
            dbname=config['dbname']
        )
        conn.autocommit = True
        return conn
    except psycopg2.Error as err:
        print(f"Database connection error: {err}")
        return None

PROGRESS_FILE = "progress_log.xlsx"

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def select_taluka(wait, taluka_name):

    try:
        taluka_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ddltahsil"))))
        taluka_dropdown.select_by_visible_text(taluka_name)
        time.sleep(5)  
    except Exception as e:
        print("selecting taluka error")

def block_feedback_popup(driver):
    try:
        driver.execute_script("document.getElementById('feedbackpopup').style.display='none';")
        print("Blocked feedback pop-up.")
    except Exception as e:
        print(f"Failed to block feedback pop-up: {e}")

# def wait_for_update_progress(wait):
   
#     try:
#         update_progress = wait.until(EC.presence_of_element_located((By.ID, "UpdateProgress1")))
#         if "display: none;" not in update_progress.get_attribute("style"):
#             wait.until(lambda driver: update_progress.get_attribute("style") == "display: none;")
#             print("UpdateProgress bar has disappeared.")
#     except Exception as e:
#         print(f"Error waiting for UpdateProgress bar to disappear: {e}")
def wait_for_update_progress(wait):
    try:
        wait.until(EC.presence_of_element_located((By.ID, "UpdateProgress1")))
        wait.until(lambda driver: not driver.find_element(By.ID, "UpdateProgress1").is_displayed())
        print("UpdateProgress bar has disappeared.")
    except Exception as e:
        print(f"Error waiting for UpdateProgress bar to disappear: {e}")


def solve_captcha(driver, wait):
    try:
        captcha_img = wait.until(EC.presence_of_element_located((By.ID, "imgCaptcha_new")))
        captcha_img.screenshot('captcha_image.png')
        captcha_image = Image.open('captcha_image.png')
        captcha_image = captcha_image.convert('L')
        captcha_text = pytesseract.image_to_string(captcha_image, config='--psm 8')
        captcha_text = ''.join(e for e in captcha_text if e.isalnum())

        print(f"Captcha text: {captcha_text}")
        # if not captcha_text:
        #     print("Captcha extraction failed. Retrying...")
        #     return solve_captcha(driver, wait)  
        return captcha_text
    except Exception as e:
        print(f"Error solving captcha: {e}")
        return ""


def click_rest_of_maharashtra_and_wait(driver, wait):
    try:
        close_button = driver.find_elements(By.CSS_SELECTOR, "a.btnclose.btn.btn-danger[style='margin-top: -300px;']")
        if close_button:
            close_button[0].click()
            print("Clicked the 'Close' button.")
            time.sleep(5)  
        rest_of_maharashtra_button = wait.until(EC.element_to_be_clickable((By.ID, "btnOtherdistrictSearch")))
        rest_of_maharashtra_button.click()
        print("Clicked the 'Rest of Maharashtra' button.")
        wait_for_update_progress(wait)  
    except Exception as e:
        print(f"Error clicking the 'Rest of Maharashtra' button: {e}")

def re_enter_details(driver, wait, taluka, village_name, property_num, year, district):
    try:
        year_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlFromYear1"))))
        year_dropdown.select_by_value(str(year))
        time.sleep(5)
        wait_for_update_progress(wait)

        district_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlDistrict1"))))
        district_dropdown.select_by_visible_text(district)
        time.sleep(5)
        wait_for_update_progress(wait)

        # Select taluka
        select_taluka(wait, taluka)

        village_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlvillage"))))
        village_dropdown.select_by_visible_text(village_name)
        time.sleep(5)
        wait_for_update_progress(wait)

        property_number = wait.until(EC.presence_of_element_located((By.ID, 'txtAttributeValue1')))
        property_number.clear()
        property_number.send_keys(str(property_num))
        property_number.send_keys(Keys.TAB)
    except Exception as e:
        print(f"Error re-entering details: {e}")

def save_data_to_db(data, year, district, taluka, village_name, property_no, page_no, attempt):
    df = pd.DataFrame(data, columns=[
        "docket_number", "docket_name", "r_date", "sro_name",
        "seller_name", "purchaser_name", "property_description",
        "sro_code", "status", "indexII"
    ]) if data else pd.DataFrame([{
        "docket_number": None, "docket_name": None, "r_date": None,
        "sro_name": None, "seller_name": None, "purchaser_name": None,
        "property_description": None, "sro_code": None, "status": "No details found", "indexII": None
    }])

    df["year"] = year
    df["district"] = district
    df["taluka"] = taluka
    df["village_name"] = village_name
    df["property_no"] = property_no
    df["page_no"] = page_no
    df["attempt"] = attempt

    conn = database_connection()
    if conn:
        cur = conn.cursor()
        for _, row in df.iterrows():
            try:
                cur.execute("""
                    INSERT INTO rest_of_maharashtra_name_based_searching (year, district, taluka, village_name, property_no, page_no, attempt,
                    docno, docket_name, r_date, sro_name, seller_name, purchaser_name, property_description, sro_code, status, indexII)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, tuple(row))
                conn.commit()
            except Exception as e:
                print(f"Database error: {e}")
                conn.rollback()
        cur.close()
        conn.close()

def enter_first_last_name(wait, first_name, last_name):
    try:
        first_name_input = wait.until(EC.presence_of_element_located((By.ID, 'txtfirstname1')))
        first_name_input.clear()
        first_name_input.send_keys(first_name)
        print(f"Entered first name: {first_name}")
        time.sleep(10)

        last_name_input = wait.until(EC.presence_of_element_located((By.ID, 'txtlastname1')))
        last_name_input.clear()
        last_name_input.send_keys(last_name)
        print(f"Entered last name: {last_name}")
        time.sleep(10)
    except Exception as e:
        print(f"Error entering names: {e}")

def click_yes_button(driver, wait):
    try:
        yes_button = wait.until(EC.element_to_be_clickable((By.ID, 'btnYesRest')))
        yes_button.click()
        print("Clicked the YES button.")
        time.sleep(10)
    except Exception as e:
        print(f"Error clicking the YES button: {e}")

def select_regular_result(driver, wait):
    try:
        regular_result_radio = wait.until(EC.presence_of_element_located((By.ID, 'propdoctype1_1')))
        regular_result_radio.click()
        print("Selected the Regular Result radio button.")
        time.sleep(5)
    except Exception as e:
        print(f"Error selecting the Regular Result radio button: {e}")


def enter_captcha_and_search(driver, wait, taluka, village_name, property_num, district, year):
    attempt = 0
    max_attempts = 6

    while attempt < max_attempts:
        attempt += 1
        try:
            print(f"\n--- Attempt {attempt} for {village_name} - {property_num} ---")

            # Fill all form details first
            re_enter_details(driver, wait, taluka, village_name, property_num, year, district)
            ensure_fields_selected(driver, wait, taluka, village_name, property_num, year, district)
            if first_name and last_name is not None:
                click_yes_button(driver, wait)
                select_regular_result(driver, wait)
                time.sleep(2)

                enter_first_last_name(wait, first_name, last_name)
                ensure_fields_selected(driver, wait, taluka, village_name, property_num, year, district)

            # Solve the NEW captcha shown after YES button
            captcha_text = solve_captcha(driver, wait)
            captcha_input = wait.until(EC.presence_of_element_located((By.ID, 'txtImg1')))
            captcha_input.clear()
            captcha_input.send_keys(captcha_text)
            print(f"Solved and entered captcha: {captcha_text}")

            # # Check if captcha value is correctly entered
            # if captcha_input.get_attribute("value").strip() != captcha_text:
            #     print("Captcha input mismatch. Re-entering...")
            #     continue

            # Click Search
            search_button = driver.find_element(By.ID, "btnSearch_RestMaha")
            search_button.click()
            print("Clicked search button.")

            # Wait for either results or "no data" message
            # WebDriverWait(driver, 15).until(
            #     lambda d: d.find_elements(By.ID, 'upRegistrationGrid') or d.find_elements(By.ID, 'lblMsgCTS1')
            # )

            # Handle results
            if driver.find_elements(By.ID, 'RegistrationGrid'):
                print("✅ Results grid loaded.")
                scrape_all_pages(wait,driver, district, taluka, village_name, property_num, attempt, year)
                return True

            elif driver.find_elements(By.ID, 'lblMsgCTS1'):
                print(" No records found.")
                take_screenshot(driver, year, district, taluka, village_name, property_num)
                save_data_to_db([], year, district, taluka, village_name, property_num, 0, attempt)
                cancel_button = wait.until(EC.element_to_be_clickable((By.ID, "btnCancel_RestMaha")))
                cancel_button.click()
                print("Clicked the cancel button to reset the form.")
                time.sleep(5)
                
                return True

        except Exception as e:
            print(f"Error during attempt {attempt}: {e}")
            take_screenshot(driver, year, district, taluka, village_name, property_num)
            time.sleep(5)
            wait_for_update_progress(wait)

    print(f"Failed after {max_attempts} attempts for property {property_num} in {village_name}")
    try:
        cancel_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnCancel_RestMaha")))
        cancel_btn.click()
    except:
        pass
    return False


def take_screenshot(driver, year, district, taluka, village_name, property_no):
    filename = f"{year}_{district}_{taluka}_{village_name}_{property_no}.png"
    filepath = os.path.join(os.getcwd(), filename)
    driver.save_screenshot(filepath)
    print(f"Screenshot saved as {filename}")

# def ensure_fields_selected(driver, wait, taluka, village_name, property_num, year, district):

#     try:
        
#         wait.until(lambda driver: len(Select(driver.find_element(By.ID, "ddlFromYear1")).options))
#         year_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlFromYear1"))))
#         if year_dropdown.first_selected_option.text != str(year):
#             year_dropdown.select_by_value(str(year))
#             print(f"Re-selected year: {year}")
#         district_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlDistrict1"))))
#         if district_dropdown.first_selected_option.text != district:
#             district_dropdown.select_by_visible_text(district)
#             print(f"Re-selected district: {district}")

#         # Verify and re-select the taluka if necessary
#         select_taluka(wait, taluka)
#         village_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlvillage"))))
#         if village_dropdown.first_selected_option.text != village_name:
#             village_dropdown.select_by_visible_text(village_name)
#             print(f"Re-selected village name: {village_name}")

#         property_number = wait.until(EC.presence_of_element_located((By.ID, 'txtAttributeValue1')))
#         if property_number.get_attribute('value') != str(property_num):
#             property_number.clear()
#             property_number.send_keys(str(property_num))
#             property_number.send_keys(Keys.TAB)
#             print(f"Re-entered property number: {property_num}")

#     except Exception as e:
#         print(f"Error ensuring fields are selected: {e}")
def ensure_fields_selected(driver, wait, taluka, village_name, property_num, year, district, retries=3):
    
    for attempt in range(retries):
        try:
            print(f"Validating form fields (attempt {attempt + 1})...")

            # YEAR
            year_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlFromYear1"))))
            selected_year = year_dropdown.first_selected_option.text.strip()
            if selected_year != str(year):
                year_dropdown.select_by_value(str(year))
                print(f"Re-selected year: {year}")
                wait_for_update_progress(wait)
                time.sleep(2)

            # DISTRICT
            district_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlDistrict1"))))
            selected_district = district_dropdown.first_selected_option.text.strip()
            if selected_district != district:
                district_dropdown.select_by_visible_text(district)
                print(f"Re-selected district: {district}")
                wait_for_update_progress(wait)
                time.sleep(2)

            # TALUKA
            taluka_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ddltahsil"))))
            selected_taluka = taluka_dropdown.first_selected_option.text.strip()
            if selected_taluka != taluka:
                taluka_dropdown.select_by_visible_text(taluka)
                print(f"Re-selected taluka: {taluka}")
                wait_for_update_progress(wait)
                time.sleep(2)

            # VILLAGE
            village_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlvillage"))))
            selected_village = village_dropdown.first_selected_option.text.strip()
            if selected_village != village_name:
                village_dropdown.select_by_visible_text(village_name)
                print(f"Re-selected village: {village_name}")
                wait_for_update_progress(wait)
                time.sleep(2)

            # PROPERTY NUMBER
            property_input = wait.until(EC.presence_of_element_located((By.ID, 'txtAttributeValue1')))
            if property_input.get_attribute('value') != str(property_num):
                property_input.clear()
                property_input.send_keys(str(property_num))
                property_input.send_keys(Keys.TAB)
                print(f"Re-entered property number: {property_num}")

            # If all successful, break out
            return

        except Exception as e:
            print(f"Retry {attempt + 1}: Error ensuring fields are selected — {e}")
            time.sleep(3)

    print("Warning: Fields could not be ensured after multiple attempts.")

def has_page_been_processed(taluka, property_num, village_name, page_num, year, district):
    progress = read_progress()
    for record in progress:
        if (record['taluka'] == taluka and str(record['property_num']) == str(property_num) and
            record['village_name'] == village_name and str(record['page_num']) == str(page_num) and
            record['year'] == year and record['district'] == district):
            return True
    return False

def write_progress(taluka, property_num, village_name, page_num, year, district):
    progress = read_progress()
    new_entry = {
        'taluka': taluka,
        'property_num': property_num,
        'village_name': village_name,
        'page_num': page_num,
        'year': year,
        'district': district
    }
    progress.append(new_entry)
    df = pd.DataFrame(progress)
    df.to_excel(PROGRESS_FILE, index=False)

def read_progress():
    if os.path.exists(PROGRESS_FILE):
        df = pd.read_excel(PROGRESS_FILE)
        return df.to_dict('records')
    return []

def scrape_all_pages(wait,driver, district, taluka, village_name, property_no, attempt, year):
    try:
        last_page_num = 1
        current_retry = 0
        max_retries = 3

        while True:
            try:
                
                table = driver.find_element(By.ID, 'RegistrationGrid')
                # rows = table.find_elements(By.XPATH, ".//tr[@style='background-color:Transparent;' or @style='background-color:AliceBlue;']")
                rows = table.find_elements(By.XPATH, ".//tr[@style='background-color:Transparent;' or @style='background-color:AliceBlue;']")
                data = []
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, 'td')
                    cols = [col.text for col in cols]
                    data.append(cols)
                # data = [[col.text for col in row.find_elements(By.TAG_NAME, 'td')] for row in rows]

                # if not data:
                #     print(f"No data found on page {last_page_num}. Taking a screenshot.")
                #     take_screenshot(driver, year, district, taluka, village_name, property_no)
                
                
                save_data_to_db(data, year, district, taluka, village_name, property_no, last_page_num, attempt)
                write_progress(taluka, property_no, village_name, last_page_num, year, district)
                current_retry = 0
                pagination_table = driver.find_element(By.XPATH, "//tr[@align='left' and @style='color:Black;background-color:#CCCCCC;']")
                page_links = pagination_table.find_elements(By.TAG_NAME, 'td')
                next_page_found = False

                for td in page_links:
                    if td.find_elements(By.TAG_NAME, 'span'):
                        span_text = td.find_element(By.TAG_NAME, 'span').text.strip()
                        if span_text.isdigit():
                            span_value = int(span_text)
                            print(f"Currently on page: {span_value}")

                    if td.find_elements(By.TAG_NAME, 'a'):
                        page_text = td.text.strip()

                        # Handle "..." to load more pages
                        if page_text == "...":
                            if last_page_num % 10 == 0:
                                print("Clicking '...' to load more pages.")
                                td.find_element(By.TAG_NAME, 'a').click()
                                WebDriverWait(driver, 20).until(EC.staleness_of(table))
                                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'RegistrationGrid')))
                                last_page_num += 1
                                next_page_found = True
                                break
                            else:
                                continue

                        # Handle numeric page navigation
                        if page_text.isdigit():
                            page_num = int(page_text)

                            if page_num > last_page_num:
                                print(f"Clicking page: {page_num}")
                                td.find_element(By.TAG_NAME, 'a').click()
                                WebDriverWait(driver, 20).until(EC.staleness_of(table))
                                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'RegistrationGrid')))
                                last_page_num = page_num
                                next_page_found = True
                                break

                if not next_page_found:
                    print("No more pages found.")
                    cancel_button = wait.until(EC.element_to_be_clickable((By.ID, "btnCancel_RestMaha")))
                    cancel_button = wait.until(EC.element_to_be_clickable((By.ID, "btnCancel_RestMaha")))
                    cancel_button.click()
                    print("Clicked the cancel button to reset the form.")
                    time.sleep(5)
                    break

            except Exception as e:
                print(f"Error scraping page {last_page_num}: {e}")
                current_retry += 1
                if current_retry >= max_retries:
                    print(f"Failed to load page {last_page_num} after {max_retries} retries. Moving to page {last_page_num + 2}.")
                    last_page_num += 2  
                    current_retry = 0
                    continue

    except Exception as e:
        print(f"An error occurred while scraping data: {e}")
        return False

def process_village_property(driver, wait, village_name, taluka, district, year):
    for property_num in range(start_number, end_number + 1):
        try:
            success = enter_captcha_and_search(driver, wait, taluka, village_name, property_num, district, year)
            if not success:
                continue
        except Exception as e:
            print(f"Error processing property number {property_num} for village {village_name}: {e}")



def process_villages(driver, wait, year, taluka, district_name):

    try:
      
        select_taluka(wait, taluka)
        print(f"Selected taluka: {taluka}")
        wait_for_update_progress(wait)
        village_dropdown = wait.until(EC.presence_of_element_located((By.ID, "ddlvillage")))
        villages = [option.text for option in Select(village_dropdown).options if option.text != "---Select Village----"]
        print(f"Villages in {taluka}: {villages}")

       
        for village_name in villages:
            try:
                # Select the village
                village_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlvillage"))))
                village_dropdown.select_by_visible_text(village_name)
                print(f"Selected village: {village_name}")
                wait_for_update_progress(wait)  
                process_village_property(driver, wait, village_name, taluka, district_name, year)
            except Exception as e:
                print(f"Error processing village {village_name}: {e}")
                continue
    except Exception as e:
        print(f"Error processing taluka {taluka}: {e}")

def process_all_districts(driver, wait):
    
    # for year in range(start_year, end_year - 1, -1):
    year_range = range(start_year, end_year - 1, -1) if start_year > end_year else range(start_year, end_year + 1)
    for year in year_range:
        try:
            
            year_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlFromYear1"))))
            year_options = [option.text for option in year_dropdown.options]
            if str(year) not in year_options:
                print(f"Year {year} is not available in the dropdown. Skipping...")
                continue
            year_dropdown.select_by_value(str(year))
            print(f"Selected year: {year}")
            wait_for_update_progress(wait)
            district_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlDistrict1"))))
            district_dropdown.select_by_visible_text(district_name)
            print(f"Selected district: {district_name}")
            wait_for_update_progress(wait)  
            taluka_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ddltahsil"))))
            talukas = [option.text for option in taluka_dropdown.options if option.text != "---Select Tahsil----"]
            print(f"Talukas in {district_name}: {talukas}")

            # Iterate through each taluka
            for taluka in talukas:
                try:
                    # Process all villages in the taluka
                    process_villages(driver, wait, year, taluka, district_name)
                except Exception as e:
                    print(f"Error processing taluka {taluka}: {e}")
                    continue
        except Exception as e:
            print(f"Error processing year {year}: {e}")
            continue

# def change_dropdown_and_crawl(url):
#     options = webdriver.ChromeOptions()
#     options.add_argument("--disable-popup-blocking")
#     driver = webdriver.Chrome(options=options)
#     driver.implicitly_wait(30)
#     try:
#         driver.get(url)
#         driver.execute_script("window.open = function(){};")
#         wait = WebDriverWait(driver, 30)
#         block_feedback_popup(driver)
#         click_rest_of_maharashtra_and_wait(driver, wait)
#         process_all_districts(driver, wait)
#     finally:
#         driver.quit()
def change_dropdown_and_crawl(
    url,
    start_year_input,
    end_year_input,
    district_name_input,
    start_number_input,
    end_number_input,
    first_name_input,
    last_name_input
):
    global start_number, end_number, start_year, end_year, district_name, first_name, last_name

    # Assign API input to global variables
    start_year = int(start_year_input)
    end_year = int(end_year_input)
    district_name = district_name_input.strip()
    start_number = int(start_number_input)
    end_number = int(end_number_input)
    first_name = first_name_input
    last_name = last_name_input

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-popup-blocking")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(30)

    try:
        driver.get(url)
        # driver.execute_script("window.open = function(){};")
        driver.execute_script("window.open = function(){};")
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "btnOtherdistrictSearch")))

        wait = WebDriverWait(driver, 30)
        block_feedback_popup(driver)
        click_rest_of_maharashtra_and_wait(driver, wait)
        process_all_districts(driver, wait)
    finally:
        driver.quit()
