import csv
import requests

# URLs for the text files
urls = {
    "casesbystate.csv": "https://tracreports.org/phptools/immigration/addressrep/state.txt",
    "casesbycounty.csv": "https://tracreports.org/phptools/immigration/addressrep/county.txt",
    "casesbysubcounty.csv": "https://tracreports.org/phptools/immigration/addressrep/cousub.txt"
}

def txt_to_csv(txt_url, csv_filename):
    response = requests.get(txt_url)
    response.raise_for_status()
    lines = response.text.strip().split('\n')
    reader = csv.reader(lines, delimiter='\t')
    rows = list(reader)
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

if __name__ == "__main__":
    for csv_file, txt_url in urls.items():
        txt_to_csv(txt_url, csv_file)