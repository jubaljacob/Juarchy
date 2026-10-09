pragma Singleton

import QtQuick
import Quickshell
import Caelestia.Config
import Caelestia.I18n
import qs.components
import qs.services
import qs.modules.nexus

Singleton {
    id: root

    function create(parent: Item, props: var): void {
        nexusComp.createObject(parent ?? dummy, props);
    }

    function openPage(pageId: string, subPage: int): var {
        const index = pageId ? PageRegistry.pages.findIndex(page => page.id === pageId) : 0;
        if (index < 0) return null;
        const win = nexusComp.createObject(dummy);
        win.openPage(index, subPage);
        return win;
    }

    QtObject {
        id: dummy
    }

    Component {
        id: nexusComp

        FloatingWindow {
            id: win
            readonly property alias nState: nexus.nState

            function openPage(index: int, subPage: int): void {
                nexus.nState.currentPageIdx = index;
                // Pages reads this stack when it loads the destination after its transition.
                nexus.nState.subPageIdxStack = subPage >= 0 ? [subPage] : [];
            }

            color: Colours.tPalette.m3surface
            surfaceFormat.opaque: false

            onVisibleChanged: {
                if (!visible)
                    destroy();
            }

            implicitWidth: nexus.implicitWidth
            implicitHeight: nexus.implicitHeight

            minimumSize.width: contentItem.Tokens.sizes.nexus.minWidth
            minimumSize.height: contentItem.Tokens.sizes.nexus.minHeight

            contentItem.Config.screen: screen.name
            contentItem.Tokens.screen: screen.name

            title: Tr.tr("Nexus — %1").arg(PageRegistry.pages[nexus.nState.currentPageIdx].label)

            Nexus {
                id: nexus

                anchors.fill: parent
                nState.screen: win.screen
                nState.isWindow: true
                onClose: win.destroy()
            }

            Behavior on color {
                CAnim {}
            }
        }
    }
}
