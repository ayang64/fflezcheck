#! /bin/sh
""":"
exec python2.7 $0 ${1+"$@"}
"""

import xml.etree.ElementTree as ElementTree
import re
import datetime
import sys, getopt
import MySQLdb
import urllib, urllib3
from lxml import etree

def fflezcheck(region,dis,sequence):
	# fflSearch.do expects the following variables.
	values = {
		'licsRegn'	:	region,
		'licsDis'		:	dis,
		'licsSeq'		:	sequence
	}

	print "2"
	http = urllib3.PoolManager()
	r = http.request('GET', 'https://www.atfonline.gov/fflezcheck/fflSearch.do', values)
	print "3"
	tree = etree.HTML(r.data)

	# Check if we received a positive result. A successful query will have
	# the words "License Number" in the element described below.
	p = tree.xpath('/html/body/table/tr/td/table/tr/td/table/tr/td/table/tr[1]/td[1]/p/b/text()')
	if len(p) != 1 or p[0] != 'License Number':
		raise Exception("FFL search failed.")
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
	
		rc = [ name, addr, city, state, zip ] 
		print "done."
		return rc

def main(argv):
	if len(argv) == 0:
		print "usage: fflezcheck [--order-number n] <region> <dis> <sequence>"
		sys.exit(2)
	try:
		opts, args = getopt.getopt(argv,"",["order-number=","cflc=","serials="])
	except getopt.GetoptError:
		print 'test.py -i <inputfile> -o <outputfile>'
		sys.exit(2)

	for opt, arg in opts:
		if opt in ("-h", "--help"):
			print 'test.py -i <inputfile> -o <outputfile>'
		if opt in ("--cflc"):
			cflc = arg
		if opt in ("--order-number"):
			order = arg
		if opt in ("--serials"):
			serials = arg

	try:
		print "1"
		(name, addr, city, state, zip) = fflezcheck(args[0],args[1],args[2])
	except:
		print "FFL ezcheck failed."
		sys.exit(2)

	# address = results[0] + "\n" + results[1] + "\n" + results[2] + ", " + results[3] + " " + results[4]
	address = name + "\n" + addr + "\n" + city + ", " + state + " " + zip


	if 'order' in locals():
		db = MySQLdb.connect('localhost', 'root', '', 'lemonstand')

		cursor = db.cursor()

		sql = " \
UPDATE \
	shop_orders \
SET \
	shipping_company='%s', \
	shipping_street_addr='%s', \
	shipping_city='%s', \
	shipping_state_id=(SELECT id FROM shop_states WHERE code LIKE '%s%%' AND country_id='1'), \
	shipping_zip='%s' \
WHERE \
	id='%s'" % ( MySQLdb.escape_string(name), MySQLdb.escape_string(addr), MySQLdb.escape_string(city), state, zip, order )
		cursor.execute(sql)


		if 'order' in locals():
			sql = " \
INSERT INTO \
	order_ffl \
	( id, order_id, region, district, sequence ) \
VALUES \
	( default, '%s', '%s', '%s', '%s') \
ON DUPLICATE KEY \
	UPDATE region='%s', district='%s', sequence='%s';" % ( MySQLdb.escape_string(order), MySQLdb.escape_string(args[0]), MySQLdb.escape_string(args[1]), MySQLdb.escape_string(args[2]), MySQLdb.escape_string(args[0]), MySQLdb.escape_string(args[1]), MySQLdb.escape_string(args[2]))
			cursor.execute(sql)

		if 'cflc' in locals():
			sql = " \
INSERT INTO \
	order_cflc_code \
	(id, order_id, cflc_auth) \
VALUES \
	(default, '%s', '%s') \
ON DUPLICATE KEY \
	UPDATE cflc_auth='%s';" % (MySQLdb.escape_string(order), MySQLdb.escape_string(cflc), MySQLdb.escape_string(cflc))
			cursor.execute(sql)

		if 'serials' in locals():
			for serial in serials.split():
				sql = "\
INSERT INTO \
	order_serial \
	(id, order_id, firearm_serial) \
VALUES \
	(default, '%s', '%s') \
ON DUPLICATE KEY \
	UPDATE firearm_serial='%s';" % (MySQLdb.escape_string(order), MySQLdb.escape_string(serial), MySQLdb.escape_string(serial)) 
				cursor.execute(sql)

		db.commit()

		# Print a message that can be pasted into the bound book.
		# FIXME: This should actually update the bound book if required.

	print address
	print args[0] + "-" + args[1] + "-XXX-XX-XX-" + args[2]
	sys.stdout.flush()

if __name__ == "__main__":
	main(sys.argv[1:])

