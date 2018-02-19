#!/usr/bin/env python
'''Flash i3 windows on focus'''
import logging as log
import os
from subprocess import (
    call,
    PIPE,
    Popen,
)
import sys
from time import sleep

import click
import i3ipc

# 0xffffffff
MAX_OPACITY = 4294967295

log.basicConfig(level=os.environ.get('LOGLEVEL', 'INFO'))

log.info('Establishing connection with i3...')
i3 = i3ipc.Connection()
log.info('Connection established')


@click.command()
@click.option('--opacity', '-o', default=0.9,
              help='Opacity of the window during a flash')
@click.option('--time', '-t', default=150, help='Flash time interval (in ms)')
@click.option('--flash_current', '-f', is_flag=True, required=False,
              help='Just flash the current window and quit')
def cli(opacity, time, flash_current):
    '''Click command line interface group'''
    opacity = format_opacity(opacity)
    if flash_current:
        flash_current_window(opacity, time)
    else:
        monitor_focus(opacity, time)


def flash_current_window(opacity, time):
    '''Flash the currently focused window'''
    focused_window_id = str(i3.get_tree().find_focused().window)
    log.info('Flashing the current window (id: %s)', focused_window_id)
    flash_window(focused_window_id, flash_opacity=opacity, time=time)


def flash_window(x_window_id, flash_opacity, time):
    '''Briefly decrease the opacity of a Xorg window'''
    seconds = time / 1000

    log.info('Flashing window %s...', x_window_id)
    default_opacity = get_window_opacity(x_window_id)

    set_opacity(x_window_id, opacity=flash_opacity)

    log.info('Waiting %sms...', time)
    sleep(seconds)

    if default_opacity:
        set_opacity(x_window_id, opacity=default_opacity)
    else:
        # Setting opacity to the max wouldn't work if the window has the
        # _NET_WM_OPAQUE_REGION defined, so we just delete the
        # _NET_WM_WINDOW_OPACITY property to return to the default
        delete_opacity_property(x_window_id)


def monitor_focus(opacity, time):
    '''Wait for changes in focus and flash windows'''
    def on_window_focus(_, event):
        '''Change in focus hook'''
        x_window_id = str(event.container.window)
        log.info('Flashing window')
        flash_window(x_window_id, flash_opacity=opacity, time=time)

        log.info('Waiting for focus event...')

    i3.on('window::focus', on_window_focus)

    log.info('Waiting for focus event...')

    i3.main()


def format_opacity(opacity):
    '''Convert the opacity paramater from decimal to int'''
    if opacity > 1 or opacity < 0:
        sys.exit("Invalid opacity argument, expected a decimal")

    return int(opacity * MAX_OPACITY)


def get_window_opacity(x_window_id):
    '''Get the opacity of a window from its Xorg window id'''
    p = Popen(['xprop', '-id', x_window_id], stdout=PIPE)

    for line in p.stdout:
        line = line.decode('utf-8').strip()
        if line.startswith('_NET_WM_WINDOW_OPACITY'):
            opacity = line.split(' ')[-1]
            log.info('Window %s has opacity = %s', x_window_id, opacity)
            return opacity

    log.info('No opacity defined for window %s', x_window_id)
    return None


def set_opacity(x_window_id, opacity):
    '''Set the opacity of a Xorg window'''
    # If opacity already defined we need to unset it first
    call(['xprop', '-id', x_window_id, '-remove', '_NET_WM_WINDOW_OPACITY'])
    call(['xprop', '-id', x_window_id, '-f', '_NET_WM_WINDOW_OPACITY', '32c',
          '-set', '_NET_WM_WINDOW_OPACITY', str(opacity)])


def delete_opacity_property(x_window_id):
    '''Delete the _NET_WM_WINDOW_OPACITY property of a Xorg window'''
    call(['xprop', '-id', x_window_id, '-remove', '_NET_WM_WINDOW_OPACITY'])
