// niamoto_hierarchical_nav.js
// Interactive hierarchical navigation tree widget for Niamoto

class NiamotoHierarchicalNav {
    constructor(config) {
        this.config = config;
        this.container = document.getElementById(config.containerId);

        if (!this.container) {
            console.error(`Navigation container #${config.containerId} not found.`);
            return;
        }

        this.items = config.items || [];
        this.params = config.params || {};
        this.currentItemId = config.currentItemId;
        this.searchInput = null;
        this.treeData = null;
        this.expandedNodes = new Set();

        // Initialize search if enabled
        if (config.searchInputId) {
            this.searchInput = document.getElementById(config.searchInputId);
            if (this.searchInput) {
                this.searchInput.addEventListener('input', (e) => this.handleSearch(e.target.value));
            }
        }

        // Build and render tree
        this.buildTree();

        // Auto-scroll to current item after a delay
        if (this.currentItemId) {
            // Increase delay to ensure DOM is fully rendered
            setTimeout(() => {
                this.scrollToCurrentItem();
            }, 500);
        }
    }

    buildTree() {
        // Determine hierarchy type and build tree structure accordingly
        if (this.params.lftField && this.params.rghtField) {
            this.treeData = this.buildNestedSetTree();
        } else if (this.params.parentIdField) {
            this.treeData = this.buildParentIdTree();
        } else if (this.params.groupByField) {
            this.treeData = this.buildGroupedTree();
        } else {
            console.error('No valid hierarchy configuration found. Need either nested set fields, parent_id_field, or group_by_field.');
            return;
        }


        // Expand path to current item BEFORE rendering
        if (this.currentItemId) {
            this.expandToItem(this.currentItemId);
        }

        // Render the tree with expanded nodes
        this.renderTree();
    }

    buildNestedSetTree() {
        // Sort items by left value
        const sorted = [...this.items].sort((a, b) =>
            (a[this.params.lftField] || 0) - (b[this.params.lftField] || 0)
        );

        const root = { children: [] };
        const stack = [root];

        for (const item of sorted) {
            const node = {
                ...item,
                children: [],
                isLeaf: (item[this.params.rghtField] - item[this.params.lftField]) === 1
            };

            // Pop stack until we find the parent
            // The parent is the one whose right value is greater than our right value
            while (stack.length > 1 &&
                   stack[stack.length - 1][this.params.rghtField] < item[this.params.rghtField]) {
                stack.pop();
            }

            // Add to parent's children
            stack[stack.length - 1].children.push(node);

            // If not a leaf, push onto stack with all necessary fields
            if (!node.isLeaf) {
                // Make sure the node has all required fields for future comparisons
                const stackNode = {
                    ...node,
                    [this.params.idField]: item[this.params.idField],
                    [this.params.rghtField]: item[this.params.rghtField]
                };
                stack.push(stackNode);
            }
        }

        return root.children;
    }

    buildParentIdTree() {
        const itemMap = new Map();
        const roots = [];

        // First pass: create all nodes
        for (const item of this.items) {
            const node = {
                ...item,
                children: []
            };
            itemMap.set(item[this.params.idField], node);
        }

        // Second pass: build hierarchy
        for (const item of this.items) {
            const node = itemMap.get(item[this.params.idField]);
            const parentId = item[this.params.parentIdField];

            if (parentId && itemMap.has(parentId)) {
                itemMap.get(parentId).children.push(node);
            } else {
                roots.push(node);
            }
        }

        return roots;
    }

    buildGroupedTree() {
        const groups = new Map();

        for (const item of this.items) {
            const groupKey = item[this.params.groupByField];
            if (!groupKey) continue;

            if (!groups.has(groupKey)) {
                const groupLabel = this.params.groupByLabelField
                    ? item[this.params.groupByLabelField]
                    : groupKey;

                groups.set(groupKey, {
                    [this.params.idField]: `group_${groupKey}`,
                    [this.params.nameField]: groupLabel,
                    isGroup: true,
                    children: []
                });
            }

            groups.get(groupKey).children.push({
                ...item,
                children: []
            });
        }

        return Array.from(groups.values());
    }

    renderTree() {
        this.container.innerHTML = this.renderNodes(this.treeData, 0);
        this.attachEventListeners();
    }

    renderNodes(nodes, level) {
        if (!nodes || nodes.length === 0) return '';

        const html = nodes.map(node => {
            const id = node[this.params.idField];
            const idStr = String(id); // Always use string IDs for consistency
            const name = node[this.params.nameField] || 'Sans nom';
            const hasChildren = node.children && node.children.length > 0;
            const isExpanded = this.expandedNodes.has(idStr);
            const isCurrent = idStr === String(this.currentItemId);
            const isGroup = node.isGroup || false;


            // Build URL for non-group items
            let url = '#';
            if (!isGroup) {
                url = this.params.baseUrl + id + '.html';
            }

            // Node classes
            const nodeClasses = [
                'tree-node',
                `tree-level-${level}`,
                hasChildren ? 'has-children' : 'leaf',
                isExpanded ? 'expanded' : '',
                isCurrent ? 'current' : '',
                isGroup ? 'group-node' : ''
            ].filter(Boolean).join(' ');

            // Chevron icon with Tailwind classes
            const chevron = hasChildren
                ? `<i class="chevron fas fa-chevron-right w-4 text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}"></i>`
                : '<span class="w-4 inline-block"></span>';

            // Content classes based on state
            const contentClasses = [
                'tree-node-content',
                'flex items-center px-2 py-1 rounded transition-colors duration-150',
                isCurrent ? 'bg-primary/10 font-semibold' : 'hover:bg-gray-100',
                isGroup ? 'font-semibold bg-gray-50 hover:bg-gray-100 cursor-pointer' : ''
            ].filter(Boolean).join(' ');

            // Link/label classes
            const linkClasses = [
                'flex-1 truncate text-sm',
                isCurrent ? 'text-primary' : 'text-gray-700 hover:text-primary',
                isGroup ? 'text-gray-900' : ''
            ].filter(Boolean).join(' ');

            // Indentation based on level (reduced from 1.5 to 1rem)
            const indent = `${level * 0.1}rem`;

            // Node HTML
            let nodeHtml = `
                <div class="${nodeClasses}" data-id="${idStr}" data-level="${level}">
                    <div class="${contentClasses}" style="padding-left: ${indent}">
                        ${chevron}
            `;

            if (isGroup) {
                nodeHtml += `<span class="${linkClasses} ml-2">${this.escapeHtml(name)}</span>`;
            } else {
                nodeHtml += `<a href="${url}" class="${linkClasses} ml-2 no-underline">${this.escapeHtml(name)}</a>`;
            }

            nodeHtml += `
                    </div>
                    ${hasChildren ? `
                        <div class="tree-children" style="display: ${isExpanded ? 'block' : 'none'}">
                            ${this.renderNodes(node.children, level + 1)}
                        </div>
                    ` : ''}
                </div>
            `;

            return nodeHtml;
        }).join('');

        return html;
    }

    attachEventListeners() {
        // Handle chevron clicks for expand/collapse
        this.container.querySelectorAll('.chevron').forEach(chevron => {
            chevron.addEventListener('click', (e) => {
                e.stopPropagation();
                const node = e.target.closest('.tree-node');
                if (node) {
                    this.toggleNode(node);
                }
            });
        });

        // Handle node content clicks (for groups)
        this.container.querySelectorAll('.group-node .tree-node-content').forEach(content => {
            content.addEventListener('click', (e) => {
                if (!e.target.classList.contains('chevron')) {
                    const node = e.target.closest('.tree-node');
                    if (node) {
                        this.toggleNode(node);
                    }
                }
            });
        });
    }

    toggleNode(node) {
        const id = node.dataset.id;
        const children = node.querySelector('.tree-children');
        const chevron = node.querySelector('.chevron');

        if (!children) return;

        if (this.expandedNodes.has(id)) {
            this.expandedNodes.delete(id);
            children.style.display = 'none';
            node.classList.remove('expanded');
            if (chevron) {
                chevron.classList.remove('rotate-90');
            }
        } else {
            this.expandedNodes.add(id);
            children.style.display = 'block';
            node.classList.add('expanded');
            if (chevron) {
                chevron.classList.add('rotate-90');
            }
        }
    }

    expandToItem(itemId) {
        // Find the item and all its ancestors
        const ancestors = this.findAncestors(this.treeData, String(itemId), []);
        if (ancestors && ancestors.length > 0) {
            // Expand all ancestors (they should already be strings from findAncestors)
            ancestors.forEach(id => {
                this.expandedNodes.add(id);
            });
        }
    }

    findAncestors(nodes, targetId, ancestors) {
        if (!nodes || nodes.length === 0) {
            return null;
        }

        for (const node of nodes) {
            const nodeId = String(node[this.params.idField]);

            if (nodeId === String(targetId)) {
                return ancestors;
            }

            if (node.children && node.children.length > 0) {
                const found = this.findAncestors(
                    node.children,
                    targetId,
                    [...ancestors, nodeId]
                );
                if (found !== null) {
                    return found;
                }
            }
        }
        return null;
    }

    handleSearch(query) {
        if (!query) {
            // Show all nodes
            this.container.querySelectorAll('.tree-node').forEach(node => {
                node.style.display = '';
            });
            return;
        }

        const lowerQuery = query.toLowerCase();
        const matchingNodes = new Set();
        const ancestorNodes = new Set();

        // Find matching nodes and their ancestors
        this.findMatches(this.treeData, lowerQuery, matchingNodes, ancestorNodes, []);

        // Update visibility
        this.container.querySelectorAll('.tree-node').forEach(node => {
            const id = node.dataset.id;
            if (matchingNodes.has(id) || ancestorNodes.has(id)) {
                node.style.display = '';

                // Expand ancestors
                if (ancestorNodes.has(id) && !this.expandedNodes.has(id)) {
                    const children = node.querySelector('.tree-children');
                    if (children) {
                        this.expandedNodes.add(id);
                        children.style.display = 'block';
                        node.classList.add('expanded');
                        const chevron = node.querySelector('.chevron');
                        if (chevron) {
                            chevron.classList.add('rotate-90');
                        }
                    }
                }
            } else {
                node.style.display = 'none';
            }
        });
    }

    findMatches(nodes, query, matchingNodes, ancestorNodes, currentAncestors) {
        for (const node of nodes) {
            const id = String(node[this.params.idField]);
            const name = (node[this.params.nameField] || '').toLowerCase();
            const matches = name.includes(query);

            if (matches) {
                matchingNodes.add(id);
                // Add all ancestors
                currentAncestors.forEach(ancestorId => ancestorNodes.add(ancestorId));
            }

            if (node.children && node.children.length > 0) {
                const hasMatchingDescendant = this.findMatches(
                    node.children,
                    query,
                    matchingNodes,
                    ancestorNodes,
                    [...currentAncestors, id]
                );

                if (hasMatchingDescendant) {
                    ancestorNodes.add(id);
                }
            }

            if (matches || (node.children && node.children.length > 0 && ancestorNodes.has(id))) {
                return true;
            }
        }
        return false;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    scrollToCurrentItem() {
        const currentNode = this.container.querySelector('.tree-node.current');
        if (!currentNode) {
            return;
        }

        // Find the scrollable container - look for the aside element which is the sidebar
        const aside = this.container.closest('aside');

        if (!aside) {
            // No aside, try to find any scrollable parent
            currentNode.scrollIntoView({ block: 'center', behavior: 'smooth' });
            return;
        }

        // Use setTimeout to ensure DOM is fully rendered
        setTimeout(() => {
            // Get the actual scrollable element within the aside
            // The aside itself might not be scrollable, but its child might be
            const scrollableElement = aside;
            const nodeRect = currentNode.getBoundingClientRect();
            const containerRect = scrollableElement.getBoundingClientRect();

            // Calculate the position relative to the scrollable container
            const relativeTop = nodeRect.top - containerRect.top + scrollableElement.scrollTop;

            // Calculate target scroll position to center the item
            const targetScroll = relativeTop - (containerRect.height / 2) + (nodeRect.height / 2);

            // Perform the scroll
            scrollableElement.scrollTo({
                top: Math.max(0, targetScroll),
                behavior: 'smooth'
            });
        }, 100); // Small delay to ensure DOM is ready
    }
}

// Make the class available globally
window.NiamotoHierarchicalNav = NiamotoHierarchicalNav;
