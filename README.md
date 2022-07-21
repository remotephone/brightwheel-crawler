# brightwheel-crawler

My kid will leave a school that uses the brightwheel app and I wanted to make sure I got all the pictures before he left. This uses selenium to crawl the page, loads all images, and then passes the auth info to requests and downloads all the image files. 

I want to add image recognition to this to be able to parse out my kids face or remove ones that are likely just updates from the school, maybe that will come later.

## Prerequisite

- Install Firefox
- Rename `sample-config.yml` to `config.yml` and fill the values

## Getting Started

```
python3 -m venv ./venv
source ./venv/bin/activate
pip3 install pyyaml
pip3 install requests
pip3 install selenium
pip3 install cryptography

python3 ./brightscraper.py
```
