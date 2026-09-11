package com.harness.memory;

import java.util.List;

/**
 * Common interface for state stores (SharedStateStore and FileStateStore).
 *
 * <p>Provides a unified API for ReviewQueue to persist review items
 * and resolutions across different backend implementations.</p>
 */
public interface StateStore {

    /**
     * Put an item into the store.
     *
     * @param item the blackboard item
     */
    void put(BlackboardItem item);

    /**
     * Get an item by ID.
     *
     * @param id item ID
     * @return the item, or null if not found
     */
    BlackboardItem get(String id);

    /**
     * List all active (non-expired) items.
     *
     * @return list of items
     */
    List<BlackboardItem> listItems();

    /**
     * Get the number of active items.
     */
    int size();
}
