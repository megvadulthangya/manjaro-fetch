#!/usr/bin/make -f

APP		    =    manjaro-iso-downloader
PREFIX      = 	/usr
PATH 	    =	$(DESTDIR)$(PREFIX)/share/bin
PATHDESKTOP =   $(DESTDIR)$(PREFIX)/share/applications
DEL 	    =  	rm -f
INSTDESK	=	install -Dm644 
INSTBIN     =   install -Dm755
	
install:
	$(INSTBIN) $(PATH) $(APP).sh
	$(INSTDESK) $(DPATH) $(APP).desktop
	mv $(PATH)/$(APP).sh $(PATH)/$(APP)

uninstall:
	$(DEL) $(PATH)/$(APP) $(DPATH)/$(APP).desktop
 
