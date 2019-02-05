from subprocess import check_output
from urllib2 import urlopen
from math import sqrt
from ping import do_one as ping

def cmd(command):
	return check_output(command, shell=True)

def checkIfNumber(string):
	numbers = list("0123456789")
	for n in numbers:
		if n in string:
			return True

	return False

print "MEDIAN XL SIGMA TSW Unofficial Lag Test Tool by *Drizak"
print ""
print "Enter number of tries per server, more pings means more precise measuring."
print "Leave blank if not sure (default=4, min=1, max=10)."

tries = 4
while(True):
	tries_input = raw_input("Tries: ")

	if tries_input == "":
		break

	try:
		tries = int(tries_input)
		if tries < 1:
			print "Please enter a integer greater or equal than 1."		
			continue
		if tries > 10:
			print "Please enter a integer lesser or equal than 10."
			continue

		else:
			break

	except:
		print "Please enter a positive integer."
		continue
	
print "Starting operation with " + str(tries) + " tries."
print ""

finalOutput = []
finalOutput.append("Ping Information (" + str(tries) + " tries)\n")
finalOutput.append("Less Average Ping (Avg) is better, less Standard Deviation (StdDev) is better, too much StdDev (StdDev > 10) means the measurement wasnt stable.\n\n")

gstxt = ""
GSDataFile_response = urlopen("REDACTED") # Sorry, admins do not want the URL to be public.
gstxt = GSDataFile_response.read().split("\n")

gsdata = []
for line in gstxt:
	line = line.strip("\n")
	data = line.split("\t")
	data = [x for x in data if x != ""]
	gsdata.append(data)

while [] in gsdata:
	gsdata.remove([])

#aquire country codes
countryCodes = []
for gs in gsdata:
	countryCode = gs[1][gs[1].index("[")+1:gs[1].index("]")]
	if countryCode not in countryCodes:
		countryCodes.append("["+countryCode+"]")

#filter by zones, manual fix when new GS are added
CC_NA = ["[us]", "[ca]"]
CC_SA = ["[br]"] 
CC_EU = ["[de]", "[cz]", "[gb]", "[uk]", "[pl]"]
CC_AS = ["[vn]", "[sg]"]
CC_OC = ["[au]"]
KW_ALL = countryCodes + ["NORTHAMERICA", "SOUTHAMERICA", "EUROPE", "ASIA", "OCEANIA"]

print ""
print "Enter a Country Code (us, au, jp, etc..) or a Keyword to filter the GS list."
print "All keywords and country codes must be separated by spaces."
print "Or leave empty for default (Pings all avaliable servers)."
print "Avaliable keywords (By continent): NORTHAMERICA, SOUTHAMERICA, EUROPE, ASIA, OCEANIA."

gsdata_filtered = []
while(True):
	key_input = raw_input("Filter by: ")

	if key_input == "":
		gsdata_filtered = gsdata
		break

	key_input = key_input.split(" ")
	key_filters_clean = [x for x in key_input if x != ""]
	key_filters = []
	for key_filter in key_filters_clean:
		if len(key_filter)==2:
			key_filters.append("["+key_filter+"]")
		else:
			key_filters.append(key_filter)

	# check for non existant keywords
	errorEncountered = False
	errorIn = ""
	for filter_kw in key_filters:
		if errorEncountered == True:
			break

		if len(filter_kw) == 2:
			if "["+filter_kw+"]" not in KW_ALL:
				errorIn = filter_kw
				errorEncountered = True
		else:
			if filter_kw not in KW_ALL:
				errorIn = filter_kw
				errorEncountered = True

	if errorEncountered == True:
		print "ERROR: " + str(errorIn).strip("[").strip("]") + " is not a valid Keyword or Country code."
		print "Please try again"
		continue

	# filter gs list
	finalFilter = []
	for filter_kw in key_filters:
		if filter_kw == "NORTHAMERICA":
			finalFilter = finalFilter + CC_NA
		elif filter_kw == "SOUTHAMERICA":
			finalFilter = finalFilter + CC_SA
		elif filter_kw == "EUROPE":
			finalFilter = finalFilter + CC_EU
		elif filter_kw == "ASIA":
			finalFilter = finalFilter + CC_AS
		elif filter_kw == "OCEANIA":
			finalFilter = finalFilter + CC_OC
		else:
			finalFilter.append(filter_kw)

	#obtain final gs list
	gsdata_filtered_dirty = []
	for filter_kw in finalFilter:
		for gs in gsdata:
			if filter_kw in gs[1]:
				gsdata_filtered_dirty.append(gs)

	#clean duplicates
	for gs in gsdata_filtered_dirty:
		if gs not in gsdata_filtered:
			gsdata_filtered.append(gs)

	break

gsdata = gsdata_filtered

print ""
print "Operation configured to start with " + str(tries) + " tries."
print ""

averagePings = [] # format: [.. [AvgPing, Identification(STR)] ..]
for gs in gsdata:
	#printing ping start
	spacer1 = 7
	pingStartString = "Pinging: " + gs[0] + " "*(spacer1-len(gs[0])) + gs[1]
	print pingStartString

	#ping, ping(ip, timeout (secs), size (bytes)), returns ping in seconds
	gs_ip = gs[2]

	pingList = []
	for t in range(tries):
		pingOutput = ping(gs_ip, 2, 32)
		
		try:
			pingOutput = int(round(1000*pingOutput,1))
		except:
			pass

		pingList.append(pingOutput)

	if None in pingList:
		print "ERROR PINGING SERVER " + gs[0] +", SKIPPING..."
		finalOutput.append(gs[0] + " "*(7-len(gs[0])) + "SKIPPED (ERROR ENCOUNTERED).\n")
		continue

	timeMin = min(pingList)
	timeMax = max(pingList)
	timeAvg = int(round(float(sum(pingList))/float(len(pingList))))
	timeStd = round(sqrt(float(sum([(x - timeAvg)**2 for x in pingList]))/float(len(pingList))),2)

	PingIdentification = gs[0] + " "*(spacer1-len(gs[0])) + gs[1]
	averagePings.append([timeAvg, PingIdentification])

	outString = ""
	spacer1 = 7
	string1 = gs[0] + " "*(spacer1-len(gs[0]))

	spacer2 = 45
	string2 = gs[1] + " "+"."*(spacer2-len(gs[1])) + " "

	spacer3 = 11
	string3 = "Min: "+str(timeMin) + " "*(spacer3-len("Min: "+str(timeMin)))

	spacer4 = 11
	string4 = "Max: "+str(timeMax) + " "*(spacer4-len("Max: "+str(timeMax)))

	spacer5 = 11
	string5 = "Avg: "+str(timeAvg) + " "*(spacer5-len(str("Avg: "+str(timeAvg))))

	spacer6 = 13
	string6 = "StdDev: "+str(timeStd) + " "*(spacer6-len(str("StdDev: "+str(timeStd))))

	outString = string1+string2+string3+string4+string5+string6+"\n"
	finalOutput.append(outString)

finalOutput.append("\n\n")
finalOutput.append("Top 5 average pings:\n")

sortedAverages = sorted(averagePings, key=lambda x: x[0])

if len(sortedAverages) >= 5:
	podium = [sortedAverages[0], sortedAverages[1], sortedAverages[2], sortedAverages[3], sortedAverages[4]]
else:
	podium = sortedAverages

for place in podium:
	spacerP = 45
	stringP = place[1] + " "+"."*(spacerP-len(place[1]+str(timeAvg))) + " " + str(place[0]) + "\n"
	finalOutput.append(stringP)

with open("output.txt","w") as f:
	f.writelines(finalOutput)

print ""
print "Operation complete, results can be found in output.txt file."
input("Press ENTER to exit.")