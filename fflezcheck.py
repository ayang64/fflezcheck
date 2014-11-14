import xml.etree.ElementTree as ElementTree
import re
import datetime
import sys
import MySQLdb
import urllib, urllib2
from lxml import etree

opener = urllib2.build_opener()
order = sys.argv[1]


# fflSearch.do expects the following variables.
values = {
	'licsRegn'	:	sys.argv[2],
	'licsDis'		:	sys.argv[3],
	'licsSeq'		:	sys.argv[4]
}

data = urllib.urlencode(values)
req = urllib2.Request('https://www.atfonline.gov/fflezcheck/fflSearch.do',data)

response = urllib2.urlopen(req)
contents = response.read()

tree = etree.HTML(contents)


# Check if we received a positive result. A successful query will have
# the words "License Number" in the element described below.
p = tree.xpath('/html/body/table/tr/td/table/tr/td/table/tr/td/table/tr[1]/td[1]/p/b/text()')
if len(p) != 1 or p[0] != 'License Number':
	print "FFL search failed."
else:
	p = tree.xpath('/html/body/table/tr/td/table/tr/td/table/tr/td/table/*')

	# Walk through results table and store premisis address.
	for t in p:
		# We try to use the trade name if possible.  If there is no trade name,
		# we use the licensee name.

		# All FFLs have Licensee names but not all have trade names.
		if t[0][0][0].text == "Trade Name":
			trade_name = t[1][0].text
		elif t[0][0][0].text == "License Name":
			licensee_name = t[1][0].text
		elif t[0][0][0].text == "Premise Address":
			addr = etree.tostring(t[1][0],method='text')
			addr_line = re.split('[\n\r]+', addr);
			addr_line = [re.sub('^\s+','',l) for l in addr_line]
			addr = addr_line[0]
			city = addr_line[1]
			sz = re.split('\s+\-\s+', addr_line[2])
			state = sz[0]
			zip = sz[1][:5] # Only copy first five characters of the zip.

	if (trade_name is not None):
		name = trade_name
	else:
		name = licensee_name

	db = MySQLdb.connect('localhost', 'root', '', 'lemonstand')

	cursor = db.cursor()

	sql = " \
UPDATE \
	shop_orders \
SET \
	shipping_company='%s', \
	shipping_street_addr='%s', \
	shipping_city='%s', \
	shipping_state_id=(SELECT id FROM shop_states WHERE code='%s'), \
	shipping_zip='%s' \
WHERE \
	id='%s'" % ( MySQLdb.escape_string(name), MySQLdb.escape_string(addr), MySQLdb.escape_string(city), state, zip, order )

	cursor.execute(sql)
	db.commit()

	# Print a message that can be pasted into the bound book.
	# FIXME: This should actually update the bound book if required.
	print "Disposed To:"
	print name
	print addr
	print city + ", " + state + " " + zip
	print sys.argv[2] + "-" + sys.argv[3] + "-XXX-XX-XX-" + sys.argv[4]
	sys.stdout.flush()

