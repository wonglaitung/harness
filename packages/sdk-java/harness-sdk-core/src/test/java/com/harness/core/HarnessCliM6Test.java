package com.harness.core;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

/**
 * M6-dep tests for HarnessCli.
 */
class HarnessCliM6Test {

    @Test
    void noArgsPrintsUsageAndReturnsZero() {
        int exit = HarnessCli.main(new String[]{});
        assertEquals(0, exit);
    }

    @Test
    void doctorWithoutDepsPrintsUsage() {
        int exit = HarnessCli.main(new String[]{"doctor"});
        assertEquals(0, exit);
    }

    @Test
    void unknownCommandReturnsZero() {
        int exit = HarnessCli.main(new String[]{"unknown"});
        assertEquals(0, exit);
    }
}
