#!/usr/bin/env python
#-*- coding: utf-8
import feedparser, time, urllib, alsaaudio
from smbus import SMBus
from bs4 import BeautifulSoup
from collections import OrderedDict
from espeak import espeak
from espeak import core as espeak_core
from subprocess import Popen, PIPE
import RPi.GPIO as GPIO
from barometric_function import readMPL3155

#readMPL3155()

global ButtonPressed, LastEncoder
ButtonPressed=0
LastEncoder=0

def synth(*args):
        global ButtonPressed
        done_synth=[False]
        def cb(event,pos,length):
          if event==espeak_core.event_MSG_TERMINATED:
                  done_synth[0]=True
        espeak.set_SynthCallback(cb)
        r = espeak.synth(*args)
        while r and not done_synth[0]:
                time.sleep(0.05)
                if ButtonPressed is not 0:
                        #ButtonPressed=0
                        done_synth[0]=True
                        print "Espeak canceled. Button ", ButtonPressed
                        espeak.cancel()
                        return r
        return r

def fSelect(dummy):
        global ButtonPressed
        print "Button pressed:",dummy," "
        ButtonPressed=dummy

def fEncoder(dummy):
        global LastEncoder
        #print "Encoder pressed:",dummy,", Previous: ",LastEncoder," "
        if (LastEncoder is 0):
          LastEncoder= dummy
        else:
          LastEncoder=0
          vol=m.getvolume()
          print "volume: ",vol[0]
          if(dummy is 9):
            m.setvolume(int(vol[0])+5)
          else:
            m.setvolume(int(vol[0])-5)

def fBack():
        global ButtonPressed
        ButtonPressed=-1

def fUp():
        global ButtonPressed
        ButtonPressed=-2


GPIO.setmode(GPIO.BCM)
#First assign GPIO pins to the "select" buttons
GPIO.setup(23,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(23,GPIO.RISING,callback=fSelect,bouncetime=400)
GPIO.setup(24,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(24,GPIO.RISING,callback=fSelect,bouncetime=400)
#Now the rotary encoder buttons
GPIO.setup(9,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(9,GPIO.RISING,callback=fEncoder,bouncetime=50)
GPIO.setup(11,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(11,GPIO.RISING,callback=fEncoder,bouncetime=50)

m=alsaaudio.Mixer(control='PCM')
p=Popen(['./tts.alsa'])
while (p.poll() is None):
  time.sleep(.6)
  pass

espeak.list_voices()
espeak.set_voice('de')

repo=OrderedDict()
with open("zeitungen.txt") as f:
        lines = f.read().splitlines()
for item in lines:
        name, link = [a.strip() for a in item.split(',')]
        repo[name] = link

#for i in repo.keys():
#       print i,repo.get(i)

def FollowLink(k,v):
        global ButtonPressed
        f=feedparser.parse(''.join(v))
        print "Follow", k, "Length ",len(f['items'])
        counter=0
        while counter<len(f['items']):
                ButtonPressed=0
                tfile = open('temp.txt', 'w')
                tfile.write(f.entries[counter].title.encode('utf-8'))
                tfile.close()
                p3=Popen(['./tts.alsa'])
                while (p3.poll() is None):
                  if ButtonPressed is 23:
#                        print "Read detail ",counter," ",ButtonPressed
                        if(p3.poll() is None):
                           print "p3 term"
                           p3.kill()
#                        print "poll OK"
                        ButtonPressed=0
                        soup=BeautifulSoup(f.entries[counter].summary.encode('utf-8'))
                        tfile = open('temp.txt', 'w')
                        tfile.write('<pitch level="50">'+soup.get_text().encode('UTF-8')+"</pitch>")
                        tfile.close()
                        p5=Popen(['./tts.alsa'])
                        print "synthing summary"
                        while (p5.poll() is None):
                           if ButtonPressed is 23:
                                if(p5.poll() is None):
                                  p5.kill()
                                  print "p5 killed"
                                ButtonPressed=0
                                synth("Artikel Laden. .")
                                html= urllib.urlopen(f.entries[counter].link).read()
                                soup=BeautifulSoup(html)
                                print k, f.entries[counter].link
                                #print soup
                                if k == 'Mainpost' or k=='Mainpost Wurzburg Stadt' or k=='Mainpost Wurzburg Land':
                                      if "pk_campaign=RSS" in str(f.entries[counter].link):
                                        link= soup.findAll(rel="canonical")
                                        start = str(link).find('href=')+6
                                        end =   str(link).find("rel")-2
                                        print start, " ", end, "  ", link, " ", str(link)[start:end]
                                        html= urllib.urlopen(str(link)[start:end]).read()
                                        soup=BeautifulSoup(html)
                                      print soup
                                      soup=soup.find("div", {"id":"detailText"})
                                if k == 'Suddeutsche':
                                      soup=soup.find("article", {"class":"article hentry"})
                                      #print soup
                                if k== 'Bayern 1' or k=='Bayern 5' or k=='B R Wissen' or k=='Studio Franken':
                                      soup=soup.find("div", {"class":"detail_inlay"})
                                      #print soup
                                if k== 'Lichtschlag eigentümlich frei':
                                      soup=soup.find("td", {"id":"main"})
                                      #print soup
                                if k== 'Junge Freiheit':
                                      soup=soup.find("main", {"class":"content"})
                                      #print soup
                                if k== 'F A Z':
                                      soup=soup.find("div", {"class":"FAZArtikelText"})
                                      #print soup
                                if k== 'Spiegel Online komplett':
                                      soup=soup.find("div", {"id":"content-main"})
                                      #print soup
                                if k== 'H R Nachrichten':
                                      soup=soup.find("div", {"class":"absatzcontent"})
                                if k== 'N Z Z':
                                      soup=soup.find("div", {"class":"newsticker-item-body"})
#                                for script in soup(["script","style"]):
#                                        soup.script.extract()
                                if soup==None:
                                        print "soup is none"
                                        break;
                                for script in soup.findAll(["script","style"]):
                                        script.extract()
                                tfile = open('temp.txt', 'w')
                                tfile.write(soup.get_text().encode('UTF-8'))
                                tfile.close()
                                p=Popen("./tts.alsa")
                                while (p.poll() is None):
                                  if ButtonPressed is not 0:
                                      if(p.poll() is None):
                                          p.kill()
                                  pass
                           elif ButtonPressed is 25:
                              p5.kill()
                              ButtonPressed=0
                              return
                           elif ButtonPressed is 24:
                               p5.kill()
                               ButtonPressed=0
                               counter-=1
                               continue
                           pass
                  #the following elifs correspond to the title
                  elif ButtonPressed is 25:
                        p3.kill()
                        ButtonPressed=0
                        return
                  elif ButtonPressed is 24:
                        p3.kill()
                        ButtonPressed=0
                        counter-=1
                        continue
                  pass
                counter+=1
                time.sleep(.7)




while 1:
   global ButtonPressed
   for k,v in repo.items():
        print k,v
        p=Popen(['espeak','-vde+f2',k])
        while (p.poll() is None):
          pass
        time.sleep(1)
        if ButtonPressed is 23:
          ButtonPressed=0
          FollowLink(k,v)
   synth("Buch Alternativlos . .")
   time.sleep(2)
   if ButtonPressed is 23:
        ButtonPressed = 0
        synth("Alternativlos Einleitung. .")
        time.sleep(1)
        if ButtonPressed is 23:
                print "Button Buch: ",ButtonPressed
                ButtonPressed = 0
                sfile = open('Buch Einleitung.txt', 'r')
                tfile = open('temp.txt', 'w')
                tfile.write(sfile.read())
                sfile.close()
                tfile.close()
                time.sleep(3)
                p=Popen("./tts.alsa")
                while (p.poll() is None):
                        pass
        for i in range (1, 10):
                synth("Alternativlos Kapitel. ."+str(i)+". . .")
                time.sleep(1)
                if ButtonPressed is 23:
                   print "Button Buch: ",ButtonPressed
                   ButtonPressed = 0
                   sfile = open('Buch '+str(i)+'.txt', 'r')
                   tfile = open('temp.txt', 'w')
                   tfile.write(sfile.read())
                   sfile.close()
                   tfile.close()
                   time.sleep(3)
                   p=Popen("./tts.alsa")
                   while (p.poll() is None):
                        pass
