import sqlite3 as lt
import sys
import re
import time
import requests
import urllib.parse

from lxml import html

BLACKLIST_FILE = "./blacklist"


def primeblacklist():
    """ Primes the newpost blacklist
    Essentially, this is a list of search terms that we will use
    to prime a list contining the postids for every post hitting that
    search term

    The blacklist is contained in a file called blacklist and
    wihen combined with a prefix url will perform a search.  The resulting
    page is parsed with lxml and a blacklist list is seeded with the extracted
    postids
    """

    b = open(BLACKLIST_FILE, "r")
    nextline = b.readline
    while nextline:
        print("{} = searchterm".format(nextline.strip)
        nextline = b.readline()

    return


def primewhitelist():
    return


def main():
    """main function"""

    # List to store tuples of all new posts that we have found
    # they will need to be stored in sqlite so we remember we've seen them
    # before!

    # create title translation table
    # map all unicode chars to None:
    # map all upper letters ascii to upper ascii
    # map all lower letters asvii to upper ascii
    # use comprehensions to create the dictionary

    primeblacklist()
    exit()
    primewhitelist()
    for urls in sys.argv[1:]:
        inmem = 0
        indb = 0
        numposts = 0
        numnewposts = 0
        newposts = []
        baseurl = urls
        dumpfile = urllib.parse.urlparse(urls).netloc
        dumpfile += ".html"
        # dumpfile = "dump.html"

        # open the database of previously visited URLs & prepare for
        # the sql statement we'll be issuing
        try:
            con = lt.connect("bp.db")
            # checkstmt = "select 'x' from posts where postid=?"
            checkstmt = "select 'x' from posts where postid=? or simpletitle=?"
            insertstmt = "insert into posts values (?,?,?,?)"
            query_cursor = con.cursor()
            insert_cursor = con.cursor()

        except:
            # aTODO add better error handling including details of err +
            # close db
            print("Error ")
            sys.exit(1)

        # open the bookmarkfile
        f = open(dumpfile, "w", encoding="utf-8")
        f.write("<p>New ads for " + baseurl + " @ " +
                time.strftime("%d/%m/%Y %H:%M:%S"))

        # Now Loop for each page 1 to 9, form URL by adding ?page=n to end
        # of baseurl
        for pagenum in range(1, 10):
            # Download the page the page of posts
            # pageurl = baseurl + "?page=" + str(pagenum)

            page = requests.get(baseurl)

            # TODO make sure it was successful
            # Convert page to an xml tree
            tree = html.fromstring(page.content)

            # get a list of all the ads matching the xpath expression
            ads = tree.xpath('//*[@id="pageBackground"]/div[2]/div[@class]/a')

            for anad in ads:
                numposts += 1
                # Extract interesting info from matching xml elements
                # tag = anad.tag
                posturl = anad.attrib["href"]
                urltext = anad.text
                newpost = False
                # simpletitle = urltext.translate(preloaded_dictionary)
                simpletitle = urltext.upper()
                simpletitle = urllib.parse.quote_plus(simpletitle)

                # extract the postid from the posturl using a regexp
                reg = re.compile('/(\d+)$')
                m = reg.search(posturl)

                # And check if it's in the database either the postid or
                # the simplified title
                if m:
                    postid = m.group(1)
                    query_cursor.execute(checkstmt, (postid, simpletitle, ))
                    # query_cursor.execute(checkstmt, (postid, ))
                    data = query_cursor.fetchone()
                    newpost = not bool(data)
                    if(data):
                        indb += 1
                    # Also check if it's in the tuple store of records we've
                    # seen this run
                    found = [i for i, v in enumerate(newposts)
                             if v[3] == simpletitle]
                    if(found):
                        inmem += 1
                    #    print(postid, simpletitle, found);

                # Write it to the dumpfile if its new and there is actually a
                # postid also add it to the newposts list for later insert
                if m and newpost and not(found):
                    numnewposts += 1
                    newposts.append((postid, baseurl, posturl, simpletitle))
                    outstr = "<li><a href='" + posturl + "'>" + urltext \
                        + "</a></li>"
                    f.write(outstr)
            # if we have any newposts then insert them
        if newposts:
            # TODO add error checking
            insert_cursor.executemany(insertstmt, newposts)
            astr = "<p></p><p>" \
                + str(numnewposts) \
                + " new posts out of " \
                + str(numposts) \
                + " dups in db " + str(indb) \
                + " dups in mem " + str(inmem) \
                + "</p>"
            f.write(astr)
        else:
            f.write("<p></p><p>No new ads</p>" +
                    " dups in db " + str(indb) +
                    " dups in mem " + str(inmem))

        # close the bookmark file & database connection
        f.close()
        con.commit()
        con.close()
    return

if __name__ == "__main__":
    main()
