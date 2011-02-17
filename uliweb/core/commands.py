##################################################################
# This module is desired by Django
##################################################################
import sys, os
from optparse import make_option, OptionParser, IndentedHelpFormatter
import uliweb
from uliweb.utils.common import log

def handle_default_options(options):
    """
    Include any default options that all commands should accept here
    so that ManagementUtility can handle them before searching for
    user commands.

    """
    if options.pythonpath:
        sys.path.insert(0, options.pythonpath)

class CommandError(Exception):
    """
    Exception class indicating a problem while executing a management
    command.

    If this exception is raised during the execution of a management
    command, it will be caught and turned into a nicely-printed error
    message to the appropriate output stream (i.e., stderr); as a
    result, raising this exception (with a sensible description of the
    error) is the preferred way to indicate that something has gone
    wrong in the execution of a command.

    """
    pass

class Command(object):
    option_list = ()
    help = ''
    args = ''
    check_apps_dirs = True
    has_options = False

    def create_parser(self, prog_name, subcommand):
        """
        Create and return the ``OptionParser`` which will be used to
        parse the arguments to this command.
    
        """
        return OptionParser(prog=prog_name,
                            usage=self.usage(subcommand),
                            version='',
                            add_help_option = False,
                            option_list=self.option_list)
    def get_version(self):
        return "Uliweb version is %s" % uliweb.version

    def usage(self, subcommand):
        """
        Return a brief description of how to use this command, by
        default from the attribute ``self.help``.
    
        """
        if self.has_options:
            usage = '%%prog %s [options] %s' % (subcommand, self.args)
        else:
            usage = '%%prog %s %s' % (subcommand, self.args)
        if self.help:
            return '%s\n\n%s' % (usage, self.help)
        else:
            return usage
    
    def print_help(self, prog_name, subcommand):
        """
        Print the help message for this command, derived from
        ``self.usage()``.
    
        """
        parser = self.create_parser(prog_name, subcommand)
        parser.print_help()
    
    def run_from_argv(self, prog, subcommand, global_options, argv):
        """
        Set up any environment changes requested, then run this command.
    
        """
        parser = self.create_parser(prog, subcommand)
        options, args = parser.parse_args(argv)
        self.execute(args, options, global_options)
        
    def execute(self, args, options, global_options):
        #todo: add translation process
        from uliweb.utils.common import check_apps_dir

        if self.check_apps_dirs:
            check_apps_dir(global_options.project)
        try:
            self.handle(options, global_options, *args)
        except CommandError, e:
            log.exception(e)
            sys.exit(1)

    def handle(self, options, global_options, *args):
        """
        The actual logic of the command. Subclasses must implement
        this method.
    
        """
        raise NotImplementedError()
    
class NewFormatter(IndentedHelpFormatter):
    def format_heading(self, heading):
        return "%*s%s:\n" % (self.current_indent, "", 'Global Options')

class NewOptionParser(OptionParser):
    def _process_args(self, largs, rargs, values):
        while rargs:
            arg = rargs[0]
            try:
                if arg[0:2] == "--" and len(arg) > 2:
                    # process a single long option (possibly with value(s))
                    # the superclass code pops the arg off rargs
                    self._process_long_opt(rargs, values)
                elif arg[:1] == "-" and len(arg) > 1:
                    # process a cluster of short options (possibly with
                    # value(s) for the last one only)
                    # the superclass code pops the arg off rargs
                    self._process_short_opts(rargs, values)
                else:
                    # it's either a non-default option or an arg
                    # either way, add it to the args list so we can keep
                    # dealing with options
                    del rargs[0]
                    raise Exception
            except:
                largs.append(arg)
    
class ApplicationCommandManager(Command):
    option_list = (
        make_option('--help', action='store_true', dest='help',
            help='show this help message and exit.'),
        make_option('-v', '--verbose', action='store_true', 
            help='Output the result in verbose mode.'),
        make_option('-s', '--settings', dest='settings', default='settings.ini',
            help='Settings file name. Default is "settings.ini".'),
        make_option('--project', default='apps',
            help='Project "apps" directory.'),
        make_option('--pythonpath', default='',
            help='A directory to add to the Python path, e.g. "/home/myproject".'),
    )
    help = ''
    args = ''
    
    def __init__(self, argv=None, commands=None, prog_name=None):
        self.argv = argv or sys.argv[:]
        self.prog_name = prog_name or os.path.basename(self.argv[0])
        self.commands = commands

    def print_help_info(self):
        """
        Returns the script's main help text, as a string.
        """
        usage = ['',"Type '%s help <subcommand>' for help on a specific subcommand." % self.prog_name,'']
        usage.append('Available subcommands:')
        commands = self.commands.keys()
        commands.sort()
        for cmd in commands:
            usage.append('  %s' % cmd)
        return '\n'.join(usage)
    
    def fetch_command(self, subcommand):
        """
        Tries to fetch the given subcommand, printing a message with the
        appropriate command called from the command line (usually
        "uliweb") if it can't be found.
        """
        try:
            klass = self.commands[subcommand]
        except KeyError:
            sys.stderr.write("Unknown command: %r\nType '%s help' for usage.\n" % \
                (subcommand, self.prog_name))
            sys.exit(1)
        return klass
    
    def execute(self):
        """
        Given the command-line arguments, this figures out which subcommand is
        being run, creates a parser appropriate to that command, and runs it.
        """
        # Preprocess options to extract --settings and --pythonpath.
        # These options could affect the commands that are available, so they
        # must be processed early.
        parser = NewOptionParser(prog=self.prog_name,
                             usage="%prog [global_options] [subcommand [options] [args]]",
                             version=self.get_version(),
                             formatter = NewFormatter(),
                             add_help_option = False,
                             option_list=self.option_list)
        
        def print_help():
            parser.print_help()
            sys.stderr.write(self.print_help_info() + '\n')
            sys.exit(1)
            
        if len(self.argv) == 1:
            print_help()
            
        global_options, args = parser.parse_args(self.argv)
        handle_default_options(global_options)
    
        try:
            subcommand = args[1]
        except IndexError:
            subcommand = 'help' # Display help if no arguments were given.
    
        if subcommand == 'help':
            if len(args) > 2:
                self.fetch_command(args[2])().print_help(self.prog_name, args[2])
                sys.exit(1)
            else:
                print_help()
        if global_options.help:
            print_help()
        else:
            self.fetch_command(subcommand)().run_from_argv(self.prog_name, subcommand, global_options, args[2:])

def execute_command_line(argv=None, commands=None, prog_name=None):
    m = ApplicationCommandManager(argv, commands, prog_name)
    m.execute()
    
if __name__ == '__main__':
    execute_command_line(sys.argv)