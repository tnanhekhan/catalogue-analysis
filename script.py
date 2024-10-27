import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os

data = []

start_url = "https://coursecatalogue.uva.nl/xmlpages/page/2024-2025-en/search-programme/programme/8205"

year_semester = start_url.split("/")[5]

csv_file_path = f"data/{year_semester.split('-en')[0]}.csv"

visited_links = set()

def save_to_csv(data):
    df = pd.DataFrame(data)
    
    if os.path.exists(csv_file_path):
        existing_df = pd.read_csv(csv_file_path)
        df = pd.concat([existing_df, df]).drop_duplicates().reset_index(drop=True)

    df.to_csv(csv_file_path, index=False)

def extract_data(url, visited):
    if url in visited:
        return
    visited.add(url)

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error while requesting {url}: {e}")
        return

    # Parse the page content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Look for the hst-container class
    hst_container = soup.find('div', class_='hst-container')

    # Debugging: Check if we found the hst-container
    if hst_container is None:
        print(f"No hst-container found for URL: {url}")
        return

    # Get the main article content
    article = hst_container.find('article', class_='twelve columns')
    if article is None:
        print(f"No article found inside hst-container for URL: {url}")
        return

    # Determine the column name based on the type of link
    if '/course/' in url:
        # For course links, use the h1 header
        header_h1 = article.find('h1')
        column_name = header_h1.get_text(strip=True) if header_h1 else "Default"
    else:
        # For program links, check headers from h2 to h4, fall back to h1
        header = article.find(['h2', 'h3', 'h4'])
        column_name = header.get_text(strip=True) if header else ""
        
        if not column_name:  # If no h2-h4 found, use h1
            header_h1 = article.find('h1')
            column_name = header_h1.get_text(strip=True) if header_h1 else "Default"

    # Get all relevant text from paragraphs, tables, and lists
    content_parts = []

    # Extract from paragraphs
    content_parts.extend(p.get_text(strip=True) for p in article.find_all('p'))

    # Extract from tables
    for table in article.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            content_parts.extend(cell.get_text(strip=True) for cell in cells)

    # Extract from lists
    for ul in article.find_all('ul'):
        for li in ul.find_all('li'):
            content_parts.append(li.get_text(strip=True))
    for ol in article.find_all('ol'):
        for li in ol.find_all('li'):
            content_parts.append(li.get_text(strip=True))

    # Join all content parts into a single string
    content = ' '.join(content_parts)

    # Check if this entry is a duplicate
    if any(entry['Column Name'] == column_name and entry['Content'] == content for entry in data):
        print(f"Duplicate entry found for {column_name}. Skipping...")
        return
    
    # Append the data as a dictionary
    data.append({'Column Name': column_name, 'Content': content})

    # Save to CSV after each extraction
    save_to_csv(data)

    # Find all links to visit in the hst-container
    links_found = hst_container.find_all('a', href=True)

    # Debugging: Print the number of links found
    print(f"Found {len(links_found)} links in {url}")

    for link in links_found:
        full_link = urljoin(url, link['href'])
        # Check if the link is valid
        if any(pattern in full_link for pattern in ['/programme/', '/course/']):
            print(f"Visiting link: {full_link}")  # Log the link being visited
            extract_data(full_link, visited)  # Recursive call for programme and course links

# Start the extraction
extract_data(start_url, visited_links)
