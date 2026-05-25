import re
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import date
from google.cloud import bigquery


def extract_salary_numbers(salary_text):
    numbers = re.findall(r"\d[\d\s]*", salary_text)
    numbers = [int(n.replace(" ", "")) for n in numbers]

    if len(numbers) == 0:
        return None, None
    elif len(numbers) == 1:
        return numbers[0], numbers[0]
    else:
        return numbers[0], numbers[1]


headers = {
    "User-Agent": "Mozilla/5.0"
}

base_url = "https://www.profesia.sk"
jobs = []

page_num = 1

while True:
    url = (
        "https://www.profesia.sk/praca/slovenska-republika/"
        f"?count_days=1&search_anywhere=data+analyst&sort_by=relevance&page_num={page_num}"
    )

    print(f"Scraping page {page_num}: {url}")

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    job_rows = soup.find_all("li", class_="list-row")

    if len(job_rows) == 0:
        print(f"No jobs found on page {page_num}. Stopping.")
        break

    for row in job_rows:
        title_link = row.select_one("h2 a")
        company = row.find("span", class_="employer")
        location = row.find("span", class_="job-location")
        salary = row.find("span", class_="label")

        if title_link:
            job_title = title_link.text.strip()
            job_url = base_url + title_link["href"]
        else:
            job_title = None
            job_url = None

        if company:
            company_text = company.text.strip()
        else:
            company_text = None

        if location:
            location_text = location.text.strip()
        else:
            location_text = None

        if salary:
            salary_text = salary.text.strip()
        else:
            salary_text = None

        salary_min_eur, salary_max_eur = extract_salary_numbers(salary_text or "")

        jobs.append({
            "collected_date": date.today(),
            "job_title": job_title,
            "company": company_text,
            "location_text": location_text,
            "salary_text": salary_text,
            "salary_min_eur": salary_min_eur,
            "salary_max_eur": salary_max_eur,
            "job_url": job_url
        })

    page_num += 1
    time.sleep(2)


df = pd.DataFrame(jobs)

if df.empty:
    print("No jobs scraped. Skipping BigQuery upload.")
    exit()

df.to_csv("jobs.csv", index=False, encoding="utf-8-sig")

print(df)
print("Saved jobs.csv")


project_id = "my-project-1-487511"
dataset_id = "job_market"
table_id = "jobs_raw"

client = bigquery.Client(project=project_id)

full_table_id = f"{project_id}.{dataset_id}.{table_id}"

job_config = bigquery.LoadJobConfig(
    write_disposition="WRITE_APPEND"
)

load_job = client.load_table_from_dataframe(
    df,
    full_table_id,
    job_config=job_config
)

load_job.result()

print(f"Loaded {len(df)} rows into {full_table_id}")