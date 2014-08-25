import sys
import argparse
import traceback
import time
import os
import paramiko
import pyinotify

from ConfigRead import ConfigRead

paramiko.util.log_to_file('/tmp/sftp_watcher.log')

wm = pyinotify.WatchManager()  # Watch Manager
mask = pyinotify.IN_CLOSE_WRITE | pyinotify.IN_OPEN | pyinotify.IN_MOVED_TO

config = None


def transferFile(sourcefile, destfile, hostname, port, user, passwd, renameflag=0):
    global config
    hostkey = None
    try:
        host_keys = paramiko.util.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
    except IOError:
        print('*** Unable to open host keys file')
        host_keys = {}

    if hostname in host_keys:
        hostkeytype = host_keys[hostname].keys()[0]
        hostkey = host_keys[hostname][hostkeytype]
        print('Using host key of type %s' % hostkeytype)

    # now, connect and use paramiko Transport to negotiate SSH2 across the connection
    try:
        t = paramiko.Transport((hostname, port))
        t.connect(username=user, password=passwd, hostkey=hostkey)
        sftp = paramiko.SFTPClient.from_transport(t)

        # if renameflag == 1:
        # sftp.put(sourcefile, os.path.join(destfile, 'C1' + time.strftime('%y%m%d_%H%M%S') + ".jpg"))
        # else:
        # sftp.put(sourcefile, os.path.join(destfile, sourcefile.split('/')[-1]))

        _destfile = ''
        print "Sourcefile Name:", sourcefile.split('/')[-1]
        if renameflag == 1:
            _destfile = os.path.join(destfile, 'C1' + time.strftime('%y%m%d_%H%M%S') + ".jpg")
            if _destfile == '':
                _destfile = destfile + '/' + 'C1' + time.strftime('%y%m%d_%H%M%S') + ".jpg"
        else:
            _destfile = os.path.join(destfile, sourcefile.split('/')[-1])
            if _destfile == '':
                _destfile = destfile + '/' + sourcefile.split('/')[-1]
        print "Dest File Path   :", _destfile
        sftp.put(sourcefile, _destfile)

        t.close()
    except Exception as e:
        print e
        # traceback.print_exc()
        try:
            t.close()
        except:
            pass
        raise e


def validate(config):
    if os.path.exists(config.WATCH_DIR_PATH) == False:
        print "%s Path does not exist" % (config.WATCH_DIR_PATH)
        sys.exit(1)
    if os.path.exists(config.BUFFER_DIR_PATH) == False:
        print "%s path does not exist" % (config.BUFFER_DIR_PATH)
        sys.exit(1)


class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CLOSE_WRITE(self, event):
        print "File writing Complete:", event.pathname, "Attempting to transfer file..."
        if event.pathname == config.WATCH_DIR_PATH:
            return
        try:
            transferFile(event.pathname, config.REMOTE_SAVE_DIR_PATH, config.REMOTE_SERVER_ADDRESS, 22,
                         config.LOGIN_NAME, config.LOGIN_PASSWORD, int(config.RENAME_FILE_FLAG))
            print "File Transfer Successful"
            try:
                os.remove(event.pathname)
                for i in os.listdir(config.BUFFER_DIR_PATH):
                    print "Moving", i, "from buffer folder for sending to", os.path.join(config.WATCH_DIR_PATH, i)
                    os.rename(os.path.join(config.BUFFER_DIR_PATH, i), os.path.join(config.WATCH_DIR_PATH, i))
            # except OSError:
            except:
                traceback.print_exc()
                pass
        except:
            print "Unable to transfer file"
            try:
                os.rename(event.pathname, os.path.join(config.BUFFER_DIR_PATH, event.pathname.split('/')[-1]))
            except:
                pass

    def process_IN_MOVED_TO(self, event):
        print "Sending buffered files:", event.pathname
        self.process_IN_CLOSE_WRITE(event)


class OpenHandler(pyinotify.ProcessEvent):
    def process_IN_OPEN(self, event):
        # print "Found New File:", event.pathname
        pass


if __name__ == "__main__":
    config = ConfigRead()
    daemon_flag = False
    parser = argparse.ArgumentParser(description='Sftp Files to Remote Destination if file changes in the watch dir')
    parser.add_argument("-c", "--configfile", type=str, help="configuration file to use")
    parser.add_argument("-d", "--daemon", type=int, help="Run as daemon?")
    args = parser.parse_args()
    if args.configfile is not None:
        if os.path.exists(args.configfile) is True:
            config = config.GetConfig(args.configfile)
            validate(config)
        else:
            print "\033[31mPlease Enter a Valid Config File Name\033[0m"
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(0)

    if args.daemon >= 1:
        daemon_flag = True
    handler = EventHandler(OpenHandler())
    notifier = pyinotify.Notifier(wm, handler)

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())

    if os.path.exists(config.WATCH_DIR_PATH):
        print "\033[32mFiring Up The watch directory monitor\033[0m"
        wdd = wm.add_watch(config.WATCH_DIR_PATH, mask, rec=True)
    else:
        print "\033[31mWatch Path Does Not Exist. Please check the configuration and try again\033[0m"
        sys.exit(1)

    if daemon_flag >= 1:
        try:
            notifier.loop(daemonize=True, pid_file='/tmp/pyinotify.pid',
                          stdout='/tmp/pyinotify.log')
        except pyinotify.NotifierError, err:
            print >> sys.stderr, err
    else:
        notifier.loop()