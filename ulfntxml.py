#!/usr/bin/env python3
# coding:utf-8
#------------------------------------------------------------------------
# File Name: createxml.py
# Author: Ego
# mail: camelzheng@msi.com Ext:2573
# Created Time: 11,29,2017 15:30:20
# SoftWare Version: 1.11
# <For ALl Fotinet TestStation>
# Update: Add RunPurpose
#------------------------------------------------------------------------

import os
import sys
import time
from urllib import request, parse
from shutil import move
from fnmatch import fnmatch
from xml.etree import cElementTree as et
from collections import OrderedDict, deque


def Uploadxml(strings="", ulxmlfile="", args0='XMLUpload?sXML=', args1='sXML'):
	URL = 'http://20.40.1.40/eps-web/upload/uploadservice.asmx/{}'.format(
		args0)
	if ulxmlfile != "":
		with open(ulxmlfile, 'rt') as f:
			strings = f.read()
	postdata = parse.urlencode([(args1, strings)])
	req = request.Request(URL)
	with request.urlopen(req, data=postdata.encode("utf-8")) as f:
		data = f.read()
		print("Server Status:{}, SeverReason:{}".format(f.status, f.reason))
	time.sleep(2)
	ele = et.XML(data)
	with open("servermesg.log", 'a+') as f:
		if ulxmlfile != '':
			f.write("ServerMesg:{}\n\n\n".format(ele.text))
	return ele.text


def Strip(text):
	return text.strip("\n").strip()


def CreateTestitemPassdict(dutobj, xpath):
	passinfo = OrderedDict()
	for i in dutobj.iter(xpath):
		for i in i.iter():
			if i.text != None and Strip(i.text) != '':
				if "SN" in xpath:
					passinfo.update({"FNT_SN": i.text})
				elif "MacAddress" in xpath:
					passinfo.update({"MAC": i.text.replace(":", '').upper()})
				else:
					print(i.tag, i.text)
					passinfo.update({i.tag: i.text})
	return passinfo


def CreateTestitemErrdict(dutobj, xpath):
	errinfo = OrderedDict()
	names = deque(maxlen=2)
	NgItem = ""
	for i in dutobj.iter(xpath):
		for i in i.iter():
			if i.text != None and Strip(i.text) != "":
				names.append(i.text)
				if i.text == "Failed" or i.text == 'Aborted':
					NgItem = names[0]
					errinfo.update({"FNT_TESTFAILITEM": names[0]})
				if "Error_Code" in i.tag:
					errinfo.update({"FNT_ERRCODE": DeleteBlank(i.text)})
				if "Error_Category" in i.tag:
					errinfo.update({"FNT_ERRCATEGORY": DeleteBlank(i.text)})
				if "Error_messsage" in i.tag:
					errinfo.update({"FNT_ERRMESG": DeleteBlank(i.text)})
			else:
				if "Error_messsage" in i.tag:
					errinfo.update({"FNT_ERRMESG": 'There are 0 alert console messages'})
	return errinfo, NgItem


def DeleteBlank(text):
	return text.replace('\n', "").replace('\t', '').replace('\r', '')\
		.replace('>', '').replace("<", '')


def CreateChildNode(parenttag, childtag, attrib):
	element = et.SubElement(parenttag, childtag, attrib)
	return element


def CreateNode(tag, attrib={}, text=None):
	element = et.Element(tag, attrib)
	element.text = text
	return element


def AddNode(parentobj, childobj):
	parentobj.append(childobj)


def CreateTestitemAttrib(value):
	return ({"Key": value})


def WriteXml(filename, root):
	ctree = et.ElementTree(root)
	ctree.write(filename)


def ConventSn(fsn):
	try:
		Mesg = Uploadxml(strings=fsn, args0="GetBarcodeByComponent?sComponentNo=", 
			args1="sComponentNo")
		with open("servermesg.log", 'a+') as f:
			if len(Mesg) > 10:
				if "FG" in Mesg:
					print("\033[32mNot Need to Convent {}.\033[0m".format(fsn))
					f.write("SN:{}\n".format(fsn))
					return fsn
				else:
					print("\033[31mConvent SN Failed: {}\033[0m".format(Mesg))
					f.write("{}\n".format(fsn))
					return fsn
			else:
				print("\033[32mConvent SN: {} ==> {} \033[0m".format(fsn, Mesg))
				f.write("SN:{}\n".format(Mesg))
				return Mesg
	except IOError as e:
		print("\033[31mError: {}; and Check Your Network\033[0m".format(e))


def CreateSingleUploadXml(dutobj, ctree, TestMachine):
	# Declare TestInfo mesg
	itemdict = OrderedDict()
	itemdict_Sn = CreateTestitemPassdict(dutobj, 'SN')
	itemdict_Mac = CreateTestitemPassdict(dutobj, 'MacAddress')
	itemdict_Bom = CreateTestitemPassdict(dutobj, 'BOM')
	itemdict_Err, NgItem = CreateTestitemErrdict(dutobj, 'Tests')
	# get Device, scriptversion, test duration
	itemdict_Testconfig = CreateTestitemPassdict(dutobj, "TestConfig")
	# Get Tester
	tester = dutobj.find(".//OPID").text
	if tester != None and Strip(tester):
		Tester = tester.replace("OP", '')
	else:
		Tester = ""
	# create root
	root = CreateNode("root")

	# create root's childs node
	childs_1 = ["TestStation", "TestMachine", "Tester", "BarcodeNo",
				"TestStatus", "Customer", "TestTime", "TestInfo", "NgInfo"]

	# create childs node
	childs_1s_text = []
	TestStation = dutobj.find(".//TestStation").text
	childs_1s_text.append(ctree.find(".//{}".format(TestStation)).text)
	childs_1s_text.append(TestMachine)
	childs_1s_text.append(Tester)
	childs_1s_text.append(ConventSn(itemdict_Sn['FNT_SN']))
	Status = "P" if dutobj.find(".//FinalResult").text == "PASS"else "F"
	childs_1s_text.append(Status)
	childs_1s_text.append("")
	childs_1s_text.append(dutobj.find(".//EndTime").text)
	childs_1s_text.append("")
	childs_1s_text.append("")

	# create root's childs
	for elem, txt in zip(childs_1, childs_1s_text):
		element = CreateNode(elem, text=txt)
		if elem == "TestInfo":
			TestInfo = element
		if elem == "NgInfo":
			NgInfo = element
		AddNode(root, element)

	# create testinfo msg
	# Ordered
	[itemdict.update({x: y}) for x, y in itemdict_Sn.items()]
	[itemdict.update({x: y}) for x, y in itemdict_Testconfig.items()]
	[itemdict.update({x: y}) for x, y in itemdict_Mac.items()]
	[itemdict.update({x: y}) for x, y in itemdict_Bom.items()]
	[itemdict.update({x: y}) for x, y in itemdict_Err.items()]

	# create TestItem Nodes
	for ikey in itemdict.keys():
		attribute = CreateTestitemAttrib(ikey)
		TestItem = CreateNode("TestItem", attribute, itemdict.get(ikey))
		AddNode(TestInfo, TestItem)

	# create ngnifo msg
	ngnodes = ["ErrCode", "Pin", "ErrPinDesc", "Location"]
	for ngelem in ngnodes:
		ngelement = CreateNode(ngelem)
		if ngelem == "ErrCode" and NgItem != "":
			ngelement.text = ctree.find(".//_{}".format(NgItem)).get("ErrCode")
		AddNode(NgInfo, ngelement)

	# Write Uploadxml
	ctime = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
	WriteXml("{}_{}_{}.xml".format(
		itemdict_Sn['FNT_SN'], TestStation, ctime), root)
	return "{}_{}_{}.xml".format(itemdict_Sn['FNT_SN'], TestStation, ctime)


def CreateAllxmlandUpload(fntxml, ctree, uploadxmlbak):
	try:
		ftree = et.parse(fntxml)
		with open("servermesg.log", 'a+') as f:
			f.write("Fortinet XML name:{}\n".format(fntxml))
	except et.ParseError as e:
		print("\033[31mFormat Error: {} in {}.\033[0m".format(e, fntxml))
		if not os.path.exists("UploadFailedFntXml"):
			os.mkdir("UploadFailedFntXml")
		print(
			"\033[5;31mNot Parsed Fortinet XML  Moved to Current Dir:UploadFailedFntXml\033[0m")
		move(fntxml, "UploadFailedFntXml")
	TestMachine = ftree.find(".//Name").text
	for dut in ftree.findall(".//DUT"):
		Uxmlname = CreateSingleUploadXml(dut, ctree, TestMachine)
		print("Start Upload Test Result... ")
		Umesg = Uploadxml(ulxmlfile=Uxmlname)
		print("\033[32mUploadXML Server Respone Mesg\033[0m\033[33m\\\ {} \033[0m".format(Umesg))
		print("------------------------------------------------------------------------")
		print("")
		# backup Uxml file
		move(Uxmlname, uploadxmlbak)


def sortfiles(filenames):
	files = [x.strip("\n") for x in filenames]
	files = sorted(files, key=os.stat)
	sfcsmcs, sfcbios, sfcos, sfctest, nonesfc = [], [], [], [], []
	for x in files:
		if "SMCS" in x:
			sfcsmcs.append(x)
		elif "SFC-BIOS" in x:
			sfcbios.append(x)
		elif "SFC-OS" in x:
			sfcos.append(x)
		elif "SFC-TEST" in x:
			sfctest.append(x)
		else:nonesfc.append(x)
	sfc = sfcsmcs + sfcbios + sfcos + sfctest
	return sfc + nonesfc 





def Parse(xml):
	try:
		tree = et.parse(xml)
		return tree
	except IOError as e:
		print("Error: {}".format(e))
	except et.ParseError as e:
		print("\033[31mFormat Error: {} in {}.\033[0m".format(e, xml))


def CheckRunPurpose(fntxml):
	ftree = Parse(fntxml)
	runpurpose = ftree.find(".//RunPurpose").text
	if runpurpose == "Product":
		return 1
	else:
		print("\033[1;34mRunPurpose: QATest\033[0m")
		os.remove(fntxml)
		return 0



def main():
	ctree = Parse("conf.xml")
	inpath = ctree.find(".//Inpath").text
	uploadxmlbak = ctree.find(".//Backuploadxml").text
	backupfntxml = ctree.find(".//Backupfntxml").text
	files = sortfiles(os.popen('find {} -maxdepth 1 -name "[0-9]*.xml" \-print'.
							   format(inpath)).readlines())
	if len(files) == 0:
		sys.stdout.write("Program is Runing, Do not Interrupt...\r")
		sys.stdout.flush()
		time.sleep(120)
	for fntxml in files:
		if CheckRunPurpose(fntxml):
			CreateAllxmlandUpload(fntxml, ctree, uploadxmlbak)
			bkfntxmlpath = "{}{}{}".format(
				backupfntxml, os.sep, os.path.basename(fntxml))
			if os.path.exists(bkfntxmlpath):
				os.remove(bkfntxmlpath)
			move(fntxml, backupfntxml)


if __name__ == '__main__':
	#Tester = raw_input("Please input your OPID: ")
	while True:
		[os.remove(x) for x in os.listdir("./")
		 if os.path.isfile(x) and fnmatch(x, "FG*.xml")]
		main()
