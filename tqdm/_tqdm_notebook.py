"""
IPython/Jupyter Notebook progressbar decorator for iterators.
Includes a default (x)range iterator printing to stderr.

Usage:
  >>> from tqdm_notebook import tnrange[, tqdm_notebook]
  >>> for i in tnrange(10): #same as: for i in tqdm_notebook(xrange(10))
  ...     ...
"""
# future division is important to divide integers and get as
# a result precise floating numbers (instead of truncated int)
from __future__ import division, absolute_import
# import compatibility functions and utilities
import sys
from ._utils import _range
# to inherit from the tqdm class
from ._tqdm import tqdm


# import IPython/Jupyter base widget and display utilities
try:  # pragma: no cover
    # For IPython 4.x using ipywidgets
    import ipywidgets
except ImportError:  # pragma: no cover
    # For IPython 3.x / 2.x
    import warnings
    with warnings.catch_warnings():
        ipy_deprecation_msg = "The `IPython.html` package has been deprecated"
        warnings.filterwarnings('error',
                                message=".*" + ipy_deprecation_msg + ".*")
        try:
            import IPython.html.widgets as ipywidgets
        except Warning as e:
            if ipy_deprecation_msg not in str(e):
                raise
            warnings.simplefilter('ignore')
            try:
                import IPython.html.widgets as ipywidgets  # NOQA
            except ImportError:
                pass
        except ImportError:
            pass

try:  # pragma: no cover
    # For IPython 4.x / 3.x
    from ipywidgets import IntProgress, HBox, HTML
except ImportError:  # pragma: no cover
    try:
        # For IPython 2.x
        from ipywidgets import IntProgressWidget as IntProgress
        from ipywidgets import ContainerWidget as HBox
        from ipywidgets import HTML
    except ImportError:
        # from ._tqdm import tqdm, trange
        # def warnWrap(fn, msg):
        #     def inner(*args, **kwargs):
        #         from sys import stderr
        #         stderr.write(msg)
        #         return fn(*args, **kwargs)
        #     return inner
        # tqdm_notebook = warnWrap(tqdm, "Warning:\n\tNo ipywidgets."
        #                          "\ntFalling back to `tqdm`.\n")
        # tnrange = warnWrap(trange, "Warning:\n\tNo ipywidgets."
        #                    "\n\tFalling back to `trange`.\n")
        # exit
        pass

try:  # pragma: no cover
    from IPython.display import display  # , clear_output
except ImportError:  # pragma: no cover
    pass

# HTML encoding
try:  # pragma: no cover
    from html import escape  # python 3.x
except ImportError:  # pragma: no cover
    from cgi import escape  # python 2.x


__author__ = {"github.com/": ["lrq3000", "casperdcl", "alexanderkuk"]}
__all__ = ['tqdm_notebook', 'tnrange']


class tqdm_notebook(tqdm):  # pragma: no cover
    """
    Experimental IPython/Jupyter Notebook widget using tqdm!
    """

    @staticmethod
    def status_printer(file, total=None, desc=None):
        """
        Manage the printing of an IPython/Jupyter Notebook progress bar widget.
        """
        # Fallback to text bar if there's no total
        # DEPRECATED: replaced with an 'info' style bar
        # if not total:
        #    return super(tqdm_notebook, tqdm_notebook).status_printer(file)

        fp = file
        if not getattr(fp, 'flush', False):  # pragma: no cover
            fp.flush = lambda: None

        # Prepare IPython progress bar
        if total:
            pbar = IntProgress(min=0, max=total)
        else:  # No total? Show info style bar with no progress tqdm status
            pbar = IntProgress(min=0, max=1)
            pbar.value = 1
            pbar.bar_style = 'info'
        if desc:
            pbar.description = desc
        # Prepare status text
        ptext = HTML()
        # Only way to place text to the right of the bar is to use a container
        container = HBox(children=[pbar, ptext])
        display(container)

        def print_status(s='', close=False, bar_style=None):
            # Note: contrary to native tqdm, s='' does NOT clear bar
            # goal is to keep all infos if error happens so user knows
            # at which iteration the loop failed.

            # Clear previous output (really necessary?)
            # clear_output(wait=1)

            # Get current iteration value from format_meter string
            if total:
                n = None
                if s:
                    npos = s.find(r'/|/')  # cause we use bar_format=r'{n}|...'
                    # Check that n can be found in s (else n > total)
                    if npos >= 0:
                        n = int(s[:npos])  # get n from string
                        s = s[npos + 3:]  # remove from string

                        # Update bar with current n value
                        if n is not None:
                            pbar.value = n

            # Print stats
            if s:  # never clear the bar (signal: s='')
                s = s.replace('||', '')  # remove inesthetical pipes
                s = escape(s)  # html escape special characters (like '?')
                ptext.value = s

            # Change bar style
            if bar_style:
                # Hack-ish way to avoid the danger bar_style being overriden by
                # success because the bar gets closed after the error...
                if not (pbar.bar_style == 'danger' and bar_style == 'success'):
                    pbar.bar_style = bar_style

            # Special signal to close the bar
            if close and pbar.bar_style != 'danger':  # hide only if no error
                container.visible = False

        return print_status

    def __init__(self, *args, **kwargs):
        # Setup default output
        if not kwargs.get('file', None) or kwargs['file'] == sys.stderr:
            kwargs['file'] = sys.stdout  # avoid the red block in IPython

        # Remove the bar from the printed string, only print stats
        if not kwargs.get('bar_format', None):
            kwargs['bar_format'] = r'{n}/|/{l_bar}{r_bar}'

        super(tqdm_notebook, self).__init__(*args, **kwargs)

        # Delete first pbar generated from super() (wrong total and text)
        self.sp('', close=True)
        # Replace with IPython progress bar display (with correct total)
        self.sp = self.status_printer(self.fp, self.total, self.desc)
        self.desc = None  # trick to place description before the bar

        # Print initial bar state
        if not self.disable:
            self.sp(self.__repr__())  # same as self.refresh without clearing

    def __iter__(self, *args, **kwargs):
        try:
            for obj in super(tqdm_notebook, self).__iter__(*args, **kwargs):
                # return super(tqdm...) will not catch exception
                yield obj
        # NB: except ... [ as ...] breaks IPython async KeyboardInterrupt
        except:
            self.sp(bar_style='danger')
            raise

    def update(self, *args, **kwargs):
        try:
            super(tqdm_notebook, self).update(*args, **kwargs)
        except Exception as exc:
            # Note that we cannot catch KeyboardInterrupt when using manual tqdm
            # because the interrupt will most likely happen on another statement
            self.sp(bar_style='danger')
            raise exc

    def close(self, *args, **kwargs):
        super(tqdm_notebook, self).close(*args, **kwargs)
        # Try to detect if there was an error or KeyboardInterrupt
        # in manual mode: if n < total, things probably got wrong
        if self.n < self.total:
            self.sp(bar_style='danger')
        else:
            if self.leave:
                self.sp(bar_style='success')
            else:
                self.sp(close=True)

    def moveto(*args, **kwargs):
        # void -> avoid extraneous `\n` in IPython output cell
        return


def tnrange(*args, **kwargs):  # pragma: no cover
    """
    A shortcut for tqdm_notebook(xrange(*args), **kwargs).
    On Python3+ range is used instead of xrange.
    """
    return tqdm_notebook(_range(*args), **kwargs)