# brightwheel-crawler v2

This python script uses selenium via <https://github.com/ultrafunkamsterdam/undetected-chromedriver> to crawl the page, loads all images, and then passes the auth info to requests and downloads all the image files.

### History

My kid will leave a school that uses the brightwheel app and I wanted to make sure I got all the pictures before he left.

I had an old version I put up never thinking anyone would use it, but I've been thrilled to hear how much use folks are getting out of it enough so that they've opened PRs and issues. Its pretty exciting to see something I threw together when I was really bad at writing code be used and appreciated by others. I've slightly less worse at python than I was when I first wrote this and the Brightwheel page has gotten noteably more reistant to scraping, so I've updated how this works and what it does.

### Future Plans

I _used to_ want to add image recognition to this to be able to parse out my kids face or remove ones that are likely just updates from the school, maybe that will come later. Nowadays, I'm happy to help this keep limping along as long as I have access to the site and can test changes.

### Requirements

1. Python 3.11+ - other versions might work but I am not using them
2. pipenv
3. A brightwheel account with a kid registered

### Installation

1. Clone this repo
2. `pipenv install`
3. `pipenv shell`

### How to use

1. Rename sample-config.yml to config.yml
2. Update config.yml with the proper email and password
3. Update config.yml with the dates your child/ren was/were enrolled and used Brightwheel
4. Run `brightscraper.py -c` to use the undetected chrome driver or `-e` to connect to a debuggable instance of chrome (see <https://github.com/remotephone/brightwheel-crawler/issues/5#issuecomment-1711859342>)
5. Chrome will open and login automatically.
6. You may be prompted for a captcha challenge. If so, I don't think this will work yet and you need to close it out and try again
7. You may be prompte for a 2FA code, enter it reasonably quickly (have your email account ready)
8. If you did not pass an index number for the kid, you will be prompted to select one
9. Wait until the script stops (returns to command prompt) and close Chrome

### Limitations

1. Photos are stored with the raw filename and do not store the date
2. Probably some others, please open an issue
