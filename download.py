import os
import sys
import requests
import json
from pathvalidate import sanitize_filename
import get_favorites  # Import the updated get_favorites_updated.py script
from tqdm import tqdm


def get_with_retry_and_fallback(url, retries=3, fallback_tld=".su", stream=False):  
    for i in range(retries):
        try:
            response = requests.get(url, stream=stream)  
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException:
            print(f"Failed to get {url}, attempt {i + 1}")
            if i == retries - 1:
                fallback_url = url.replace(".party", fallback_tld)
                print(f"Retrying with fallback URL: {fallback_url}")
                for j in range(retries):
                    try:
                        fallback_response = requests.get(fallback_url, stream=stream)
                        fallback_response.raise_for_status()
                        return fallback_response
                    except requests.exceptions.RequestException:
                        print(f"Failed to get {fallback_url}, attempt {j + 1}")
                        if j == retries - 1:
                            print(f"Failed to download {fallback_url}, logging to download_errors.txt")
                            with open("download_errors.txt", 'a') as error_file:
                                error_file.write(f"{fallback_url}\\n")


def download_file(url, folder_name, file_name, artist_url):
    # sourcery skip: extract-method
    folder_path = os.path.join(folder_name, file_name)
    if os.path.exists(folder_path):
        print(f"Skipping download: {file_name} already exists in the folder.")
        return

    response = get_with_retry_and_fallback(url, stream=True)
    if response and response.status_code == 200:
        total_size_in_bytes = int(response.headers.get('content-length', 0))
        progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True, leave=False)

        with open(folder_path, 'wb') as f:
            for data in response.iter_content(1024):
                progress_bar.update(len(data))
                f.write(data)

        progress_bar.close()

        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            print("ERROR, something went wrong")

        # Clear the console, move the cursor to the previous line, and clear the line
        os.system('cls' if os.name == 'nt' else 'clear')
        sys.stdout.write("\033[F")  # Move the cursor to the previous line
        sys.stdout.write("\033[K")  # Clear the line
        print(f"Downloading files from {artist_url}:")
        print(f"Downloading: {file_name}")


def run_with_base_url(url_list):
    try:
        for url in tqdm(url_list, desc="Downloading pages..."):
            # Extract the domain, platform, and artist name from the URL
            url_parts = url.split("/")
            domain = url_parts[2].split(".")[0]
            platform = url_parts[4]
            artist_name = url_parts[6].split("?")[0]  # Split the artist's name by the question mark and take the first part

            # Construct the folder structure
            artists_folder = "Creators"
            domain_folder = os.path.join(artists_folder, domain)
            artist_folder = os.path.join(domain_folder, sanitize_filename(artist_name))
            platform_folder = os.path.join(artist_folder, sanitize_filename(platform))

            os.makedirs(platform_folder, exist_ok=True)

            # Download the page and parse it as JSON
            response = get_with_retry_and_fallback(url)
            data = json.loads(response.text)

            # total_posts = sum(len(page_data) for page_data in data)

            for post_num, post in enumerate(data, start=1):
                post_folder_name = sanitize_filename(post.get('title', ''))
                post_folder_path = os.path.join(platform_folder, post_folder_name)
                os.makedirs(post_folder_path, exist_ok=True)

                base_url = "/".join(url.split("/")[:3])  # Extract the base URL

                for attachment in post.get('attachments', []):
                    attachment_url = base_url + attachment.get('path', '')
                    attachment_name = attachment.get('name', '')
                    if attachment_url and attachment_name:
                        download_file(attachment_url, post_folder_path, attachment_name, url)

                file_info = post.get('file')
                if file_info and 'name' in file_info and 'path' in file_info:
                    file_url = base_url + file_info['path']
                    file_name = file_info['name']
                    if file_url and file_name:
                        download_file(file_url, post_folder_path, file_name, url)

                content = post.get('content', '')
                save_content_to_txt(post_folder_path, content)

                # print(f"Post {post_num}/{total_posts}")

        return True
    except requests.exceptions.RequestException:
        return False


def save_content_to_txt(folder_name, content):
    folder_path = os.path.join(folder_name, "content.txt")
    with open(folder_path, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    valid_options = ["kemono", "coomer", "both"]  
    user_option = input(f"Please enter your choice: ({', '.join(valid_options)}): ")
    while user_option not in valid_options:
        user_option = input(f"Invalid choice. Please enter your choice ({', '.join(valid_options)}): ")

    options = [user_option] if user_option != "both" else ["kemono", "coomer"]

    for option in options:
        url_list = get_favorites.main(option)   

        run_with_base_url(url_list)


if __name__ == "__main__":
    main()