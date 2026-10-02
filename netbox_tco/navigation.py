from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem

menu = PluginMenu(
    label='TCO',
    icon_class='mdi mdi-currency-usd',
    groups=(
        ('Procurement', (
            PluginMenuItem(
                link='plugins:netbox_tco:qpi_list',
                link_text='QPIs',
                permissions=['netbox_tco.view_qpi'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_tco:qpi_add',
                        title='Add',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_tco.add_qpi'],
                    ),
                ),
            ),
        )),
        ('Contracts & Licenses', (
            PluginMenuItem(
                link='plugins:netbox_tco:supportcontract_list',
                link_text='Support Contracts',
                permissions=['netbox_tco.view_supportcontract'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_tco:supportcontract_add',
                        title='Add',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_tco.add_supportcontract'],
                    ),
                ),
            ),
            PluginMenuItem(
                link='plugins:netbox_tco:coverageline_list',
                link_text='Line Items',
                permissions=['netbox_tco.view_coverageline'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_tco:coverageline_add',
                        title='Add',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_tco.add_coverageline'],
                    ),
                ),
            ),
            PluginMenuItem(
                link='plugins:netbox_tco:license_list',
                link_text='Licenses',
                permissions=['netbox_tco.view_license'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_tco:license_add',
                        title='Add',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_tco.add_license'],
                    ),
                ),
            ),
            PluginMenuItem(
                link='plugins:netbox_tco:licenseline_list',
                link_text='Line Items',
                permissions=['netbox_tco.view_licenseline'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_tco:licenseline_add',
                        title='Add',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_tco.add_licenseline'],
                    ),
                ),
            ),
        )),
        ('Lifecycle', (
            PluginMenuItem(
                link='plugins:netbox_tco:lifecyclerecord_list',
                link_text='EOS/EOL Records',
                permissions=['netbox_tco.view_lifecyclerecord'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_tco:lifecyclerecord_add',
                        title='Add',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_tco.add_lifecyclerecord'],
                    ),
                ),
            ),
        )),
        ('Lookups', (
            PluginMenuItem(
                link='plugins:netbox_tco:servicelevel_list',
                link_text='Service Levels',
                permissions=['netbox_tco.view_servicelevel'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_tco:servicelevel_add',
                        title='Add',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_tco.add_servicelevel'],
                    ),
                ),
            ),
            PluginMenuItem(
                link='plugins:netbox_tco:licensetype_list',
                link_text='License Types',
                permissions=['netbox_tco.view_licensetype'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_tco:licensetype_add',
                        title='Add',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_tco.add_licensetype'],
                    ),
                ),
            ),
            PluginMenuItem(
                link='plugins:netbox_tco:milestonetype_list',
                link_text='EOx Milestones',
                permissions=['netbox_tco.view_milestonetype'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_tco:milestonetype_add',
                        title='Add',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_tco.add_milestonetype'],
                    ),
                ),
            ),
        )),
    ),
)
