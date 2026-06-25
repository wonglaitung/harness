package com.harness.core;

/**
 * Global usage statistics.
 */
public class GlobalUsage {

    private double dailyCostUsd = 0.0;
    private int dailyTokens = 0;

    public double getDailyCostUsd() {
        return dailyCostUsd;
    }

    public int getDailyTokens() {
        return dailyTokens;
    }

    public void addCost(double costUsd) {
        dailyCostUsd += costUsd;
    }

    public void addTokens(int tokens) {
        dailyTokens += tokens;
    }

    public void reset() {
        dailyCostUsd = 0.0;
        dailyTokens = 0;
    }
}
