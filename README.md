# brightwheel-crawler
This python script uses selenium to crawl the page, loads all images, and then passes the auth info to requests and downloads all the image files. 

### History
My kid will leave a school that uses the brightwheel app and I wanted to make sure I got all the pictures before he left. 

### Future Plans
I want to add image recognition to this to be able to parse out my kids face or remove ones that are likely just updates from the school, maybe that will come later.

### Requirements
1. Firefox needs to be installed on the same device
2. pyyaml must be installed (python -m pip install pyyaml)
3. This was known to work with Python3.10 and FireFox 100.0.1.  No guarantees with other versions of either application.

### How to use
1. Rename sample-config.yml to config.yml
2. Update config.yml with the proper email and password
3. Update config.yml with the dates your child/ren was/were enrolled and used Brightwheel
4. Run brightscraper.py
5. FireFox will open and login automatically.
6. Click the child you wish to download photos.
7. Wait until the script stops (returns to command prompt) and close FireFox

### Limitations
1. With multiple children, you will need to run this multiple times and click on the child to download each time
2. Photos are stored with the raw filename and do not store the date
