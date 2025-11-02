from bs4 import BeautifulSoup
import requests, os, csv, re
import argparse
import time

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LogoScraper/1.0)"}


def load_teams_from_file(filename: str) -> list:
    teams = []  # [[Team name , homepage url],[Team name , homepage url]] when completed

    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), filename)
    with open(path, "r", encoding="utf-8") as domain_file:
        parser = csv.reader(domain_file)

        headers = next(parser)
        for row in parser:
            if len(row) != 2:
                print(f"[ERROR] Bad row, not correctly formated: {row} ")
                continue
            teams.append(row)

    print(f"[INFO] Done geting {headers[0]} and {headers[1]} for {len(teams)} teams")
    return teams


def get_sponsor_logo_urls(teams: list) -> list:
    # [[Team name , (sponsor_label, logo_url)], [Team name , (sponsor_label, logo_url)]]
    all_team_sponsors = []

    for team in teams:
        logo_urls = []
        team_name = clean_name(team[0])
        team_url = team[1]

        try:
            response = requests.get(
                team_url,
                timeout=10,
                headers=HEADERS,
            )

            response.raise_for_status()
        except requests.RequestException as e:
            print(f"[ERROR] Failed to fetch:{e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        sponsor_images = soup.find_all("img", attrs={"class": "partners__logo__img"})
        for img in sponsor_images:
            sponsor_label = img.find_previous("div", class_="partners__label")

            if not sponsor_label:
                print("[WARN] Could not find sponsor type, disregarding")
                continue

            # label the sponsor for sorting
            sponsor_label = clean_name(sponsor_label.get_text(strip=True))

            src = img.get("src")
            logo_urls.append((sponsor_label, src))

        all_team_sponsors.append([team_name, logo_urls])
        # as to not overwhelm the servers
        time.sleep(0.5)

    return all_team_sponsors


def download_sponsor_images(all_team_sponsors: list):
    folder_path = os.path.join(os.curdir, "logos")
    number_of_images = 0
    failed_downloads = []
    for team in all_team_sponsors:
        team_name = team[0]
        sponsor_urls = team[1]
        team_path = os.path.join(folder_path, f"{team_name.lower()}")

        if not sponsor_urls:
            continue

        os.makedirs(team_path, exist_ok=True)

        for i, sponsors in enumerate(sponsor_urls):
            sponsor_label, url = sponsors

            try:
                image_name = extract_filename(url)

            except ValueError as e:
                print("[WARN] Could not parse filename, using default name")
                image_name = f"nr_{i}.jpg"

            # create a folder for each lable that the images are stored in.
            label_path = os.path.join(team_path, sponsor_label)
            os.makedirs(label_path, exist_ok=True)

            image_path = os.path.join(label_path, f"{image_name}")

            if os.path.exists(image_path):
                continue

            try:
                response = requests.get(
                    url,
                    stream=True,
                    timeout=10,
                    headers=HEADERS,
                )

                response.raise_for_status()

            except requests.RequestException as e:
                print("[ERROR] Failed to fetch url: ", e)
                failed_downloads.append(url)
                continue

            with open(image_path, "wb") as image:
                for block in response.iter_content(1024):
                    if not block:
                        break
                    image.write(block)

            number_of_images += 1
            # as to not overwhelm the servers
            time.sleep(0.5)

        print(f"[DONE] Download finished for {team_name}")

    print(f"[DONE] Finished downloading all {number_of_images} team sponsor images")

    if failed_downloads:
        print("[INFO] FAILED DOWNLOADS:")
        for fd in failed_downloads:
            print(fd)


def extract_filename(url: str) -> str:
    match = re.search(r"/([^/]+?)\.(png|jpg|jpeg|webp)$", url, re.IGNORECASE)
    if not match:
        raise ValueError(url)

    # make alphanumerical and add back file extension
    filename = f"{clean_name(match.group(1))}.{match.group(2)}"
    return filename


def clean_name(name):
    return re.sub(r"[^A-Za-z0-9_æøåÆØÅ-]+", "_", name.strip("_")).lower()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Path to a csv file of teams and homepage urls")
    parser.add_argument(
        "--test", action="store_true", help="Run test run with a single club"
    )
    args = parser.parse_args()

    if args.test:
        test_team = [["Vålerenga Fotball", "https://www.vif-fotball.no"]]
        test_team_sponsors = get_sponsor_logo_urls(test_team)
        download_sponsor_images(test_team_sponsors)
        return

    teams = load_teams_from_file(args.file)
    all_team_sponsors = get_sponsor_logo_urls(teams)
    download_sponsor_images(all_team_sponsors)


if __name__ == "__main__":
    main()
