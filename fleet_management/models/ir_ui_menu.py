from odoo import models, api, tools

class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    @tools.ormcache_context('self._uid', 'debug', keys=('lang',))
    def load_menus(self, debug):
        # Retrieve the menus from super
        cached_menus = super(IrUiMenu, self).load_menus(debug)
        
        fleet_root_menu = self.env.ref('fleet_management.menu_fleet_management_root', raise_if_not_found=False)
        if not fleet_root_menu or fleet_root_menu.id not in cached_menus:
            return cached_menus

        # Create a deep copy of the dictionaries to avoid modifying the global cache
        all_menus = {k: dict(v) if isinstance(v, dict) else v for k, v in cached_menus.items()}
        for k, v in all_menus.items():
            if isinstance(v, dict) and 'children' in v:
                v['children'] = list(v['children'])

        fleet_app_id = fleet_root_menu.id

        def get_all_descendants(menu_id):
            descendants = []
            menu = all_menus.get(menu_id)
            if menu and menu.get('children'):
                for child_id in menu['children']:
                    descendants.append(child_id)
                    descendants.extend(get_all_descendants(child_id))
            return descendants

        fleet_descendants = get_all_descendants(fleet_app_id)

        changed = True
        while changed:
            changed = False
            for menu_id in list(fleet_descendants):
                menu = all_menus.get(menu_id)
                if not menu or menu.get('action'):
                    continue # Not a folder, or already removed
                
                children = menu.get('children', [])
                if len(children) == 1:
                    child_id = children[0]
                    child = all_menus.get(child_id)
                    parent_id = menu.get('parent_id')
                    
                    if child and parent_id:
                        parent_id = parent_id[0]
                        parent = all_menus.get(parent_id)
                        if parent:
                            # 1. Remove folder from parent's children
                            if menu_id in parent['children']:
                                idx = parent['children'].index(menu_id)
                                parent['children'][idx] = child_id
                            
                            # 2. Update child's parent_id
                            child['parent_id'] = [parent_id, parent.get('name', '')]
                            
                            # 3. Delete folder
                            del all_menus[menu_id]
                            if menu_id in fleet_descendants:
                                fleet_descendants.remove(menu_id)
                            
                            changed = True
                            break

        return all_menus
