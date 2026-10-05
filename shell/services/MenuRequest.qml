pragma Singleton

import Quickshell

Singleton {
    property string section: ""
    property var targetState: null
    property bool pending: false
    property int revision: 0

    function request(name: string, state: var): void {
        section = name;
        targetState = state;
        pending = true;
        revision++;
    }
}
