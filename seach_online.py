import requests
import socket
import json
import socket
import json
from bs4 import BeautifulSoup


# Function to perform Google Custom Search API query
def get_google_search_results(company_name, api_key, cse_id):
    query = f'"{company_name}" company'
    url = 'https://www.googleapis.com/customsearch/v1'
    params = {
        'q': query,
        'key': api_key,
        'cx': cse_id
    }
    response = requests.get(url, params=params)
    return response.json()


# Function to extract and analyze search results
def analyze_search_results(company_name, response):
    items = response.get('items', [])
    company_keywords = ['company', 'inc', 'ltd', 'llc', 'corporation', 'corp', 'gmbh', 'pty', 'plc']
    company_found = False
    for item in items:
        title = item.get('title', '').lower()
        snippet = item.get('snippet', '').lower()
        link = item.get('link', '').lower()

        # Check if the company name is in the title or snippet
        if company_name.lower() in title or company_name.lower() in snippet:
            # Check for company-related keywords
            if any(keyword in title or keyword in snippet for keyword in company_keywords):
                company_found = True
                break

        print(title, snippet, link)
        # Check if the company name is in the link
        if company_name.lower() in link:
            company_found = True
            break
    return company_found


# Function to check if the company's domain exists
def check_domain(company_name):
    possible_domains = [
        f"{company_name.lower().replace(' ', '')}.com",
        f"{company_name.lower().replace(' ', '')}.net",
        f"{company_name.lower().replace(' ', '')}.org"
    ]
    domain_found = False
    for domain in possible_domains:
        try:
            socket.gethostbyname(domain)
            domain_found = True
            break
        except socket.error:
            continue
    return domain_found


# Function to calculate the composite risk score
def calculate_risk_score(search_found, domain_exists):
    score = 100
    if search_found:
        score -= 40
    if domain_exists:
        score -= 30
    return max(score, 0)


# Main function
def assess_company_risk(company_name, api_key, cse_id):
    print(f"Assessing risk for company: {company_name}")
    # 1. Check Google Search Results
    print("Checking internet presence via Google Search...")
    response = get_google_search_results(company_name, api_key, cse_id)
    search_found = analyze_search_results(company_name, response)
    print(f"Internet presence found: {search_found}")

    # 2. Check Domain Existence
    print("Checking domain existence...")
    domain_exists = check_domain(company_name)
    print(f"Domain exists: {domain_exists}")

    # 4. Calculate Risk Score
    risk_score = calculate_risk_score(search_found, domain_exists)
    print(f"The risk score for {company_name} is {risk_score}")
    return risk_score


# Usage Example
if __name__ == "__main__":
    # Replace with your actual API keys
    api_key = 'AIzaSyDeS3wLMXh9sATfe5qUHOb80O22cCw1Z2s'
    cse_id = '173220168829c4888'
    company_name = 'ALSALAM CITY GENERAL CONTRACTING'

    # Call the main function
    assess_company_risk(company_name, api_key, cse_id)
