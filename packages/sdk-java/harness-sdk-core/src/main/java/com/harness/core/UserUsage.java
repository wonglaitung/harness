package com.harness.core;

import com.harness.types.CostConfig;

/**
 * User usage statistics.
 */
public class UserUsage {

    private final String userId;
    private int dailyTokens = 0;
    private int hourlyRequests = 0;
    private String date = "";
    private int hour = 0;

    public UserUsage(String userId) {
        this.userId = userId;
    }

    public String getUserId() {
        return userId;
    }

    public int getDailyTokens() {
        return dailyTokens;
    }

    public int getHourlyRequests() {
        return hourlyRequests;
    }

    public String getDate() {
        return date;
    }

    public int getHour() {
        return hour;
    }

    public void addTokens(int tokens) {
        dailyTokens += tokens;
    }

    public void addRequest() {
        hourlyRequests++;
    }

    /**
     * Check budget against config.
     *
     * @return array of [isWithinBudget, warningMessage]
     */
    public Object[] checkBudget(CostConfig config) {
        String warning = null;

        if (dailyTokens > config.dailyTokenLimit()) {
            warning = String.format("Daily token limit exceeded: %d/%d", dailyTokens, config.dailyTokenLimit());
            return new Object[]{false, warning};
        }

        if (hourlyRequests > config.hourlyRequestLimit()) {
            warning = String.format("Hourly request limit exceeded: %d/%d", hourlyRequests, config.hourlyRequestLimit());
            return new Object[]{false, warning};
        }

        double tokenRatio = (double) dailyTokens / config.dailyTokenLimit();
        if (tokenRatio >= config.warningThreshold()) {
            warning = String.format("Token usage at %.0f%% of daily limit", tokenRatio * 100);
        }

        return new Object[]{true, warning};
    }
}
