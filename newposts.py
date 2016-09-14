import sqlite3 as lt
import sys
import re
import time
import requests
import urllib.parse
from lxml import html


BLACKLIST_FILE = "./blacklist"


def getads(url):
    """ Given a url request it and use lxml to return a list of the ads it contains
    :param url: a url to a list of ads
    :return: a list of urls containing the ads
    """
    page = requests.get(url)

    # TODO make sure it was successful
    # Convert page to an xml tree
    tree = html.fromstring(page.content)

    # get a list of all the ads matching the xpath expression
    ads = tree.xpath('//*[@id="pageBackground"]/div[2]/div[@class]/a')
    return ads


def extractpostid(url):
    """ Given a url extract the trailing postid portion
    :param url: a url to a bp ad post which contains postid at the end
    :return: the postid as string or none
    """

    # compile the regexp which matches the url + isolates the post portion
    reg = re.compile('/(\d+)$')
    m = reg.search(url)

    # Extract the postid from the regexp pattern match
    if m:
        return m.group(1)
    else:
        return None;


def primeblacklist(url):
    """ Primes the newpost blacklist
    Essentially, this is a list of search terms that we will use
    to prime a list containing the postids for every post hitting that
    search term

    The blacklist is contained in a file called blacklist and
    wihen combined with a prefix url will perform a search.  The resulting
    page is parsed with lxml and a blacklist list is seeded with the extracted
    postids
    """

    blacklisturls = []
    blacklistpostids = []
    postid = None;
    b = open(BLACKLIST_FILE, "r")
    nextline = str(b.readline())
    nextline = nextline.strip()
    while nextline:
        blacklisturls.append(url+"?keyword={}".format(nextline))
        print("{} = searchterm".format(nextline))
        nextline = b.readline().strip()

    # Now iterate through the urls with the search term appended
    # get the page(s) of results and extract the post ids

    for searchurl in blacklisturls:
        blacklistedresults = getads(searchurl)
        #print("Blacklist for {}".format(searchurl))
        for posturlelement in blacklistedresults:
            posturl = posturlelement.attrib["href"]
            #print("\tBlacklisturl: {}".format(posturl))
            postid = extractpostid(posturl)
            blacklistpostids.append(postid)

    return blacklistpostids


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

    for urls in sys.argv[1:]:
        blackposts = []
        inmem = 0
        indb = 0
        numposts = 0
        numnewposts = 0
        newposts = []
        baseurl = urls
        dumpfile = urllib.parse.urlparse(urls).netloc
        dumpfile += ".html"
        blacklistedposts = 0
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

        # Now prime the blacklist for this URL

        blackposts=primeblacklist(urls)
        # Now Loop for each page 1 to 9, form URL by adding ?page=n to end
        # of baseurl
        for pagenum in range(1, 3):
            # Download the page the page of posts
            # pageurl = baseurl + "?page=" + str(pagenum)

            pageurl = baseurl + "?page=" + str(pagenum)
            ads = getads(pageurl)

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

                # And check if it's in the database either the postid or
                # the simplified title
                postid = extractpostid(posturl)
                blacklisted = False
                found = False
                newpost = False

                if postid:
                    if postid in blackposts:
                        blacklisted=True
                        blacklistedposts += 1
                    else:
                        query_cursor.execute(checkstmt, (postid, simpletitle, ))
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
                # If blacklisted OR we've seen before OR it's in db OR its fucked, skip it
                if blacklisted or found or not(newpost) or not(postid):
                    pass;
                else: # it's legitimately new write it out
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
                + " blacklisted " + str(blacklistedposts) \
                + " posts on blacklist: {} ".format(len(blackposts)) \
                + "</p>"
            f.write(astr)
        else:
            f.write("<p></p><p>No new ads</p>" +
                    " dups in db " + str(indb) +
                    " dups in mem " + str(inmem) +
                    " blacklisted posts {}".format(str(blacklistedposts)) +
                    " posts on blacklist: {}".format(len(blackposts)))

        # close the bookmark file & database connection
        f.close()
        con.commit()
        con.close()
    return

if __name__ == "__main__":
    main()
