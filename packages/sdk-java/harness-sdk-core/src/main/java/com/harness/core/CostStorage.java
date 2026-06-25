package com.harness.core;

import java.sql.*;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.types.TokenUsage;

/**
 * Cost storage interface for multi-level budget tracking.
 *
 * Provides storage backends for tracking user-level and global-level usage.
 *
 * Example:
 * <pre>
 * CostStorage storage = new InMemoryCostStorage();
 *
 * // Record user usage
 * UserUsage usage = storage.recordUserUsage("user-123", 1000, 500, true);
 *
 * // Check budget
 * boolean withinBudget = usage.checkBudget(config);
 *
 * // Get global usage
 * GlobalUsage global = storage.getGlobalUsage();
 * </pre>
 */
public interface CostStorage {

    /**
     * Get usage for a user.
     */
    UserUsage getUserUsage(String userId);

    /**
     * Record usage for a user.
     */
    UserUsage recordUserUsage(String userId, int inputTokens, int outputTokens, boolean request);

    /**
     * Get global usage.
     */
    GlobalUsage getGlobalUsage();

    /**
     * Record global usage.
     */
    GlobalUsage recordGlobalUsage(double costUsd, int tokens);

    /**
     * Reset daily counters.
     */
    void resetDaily();

    // -------------------------------------------------------------------------
    // User Usage
    // -------------------------------------------------------------------------

    /**
     * User-level usage statistics.
     */
    class UserUsage {
        private final String userId;
        private int dailyTokens;
        private int hourlyRequests;
        private String date;
        private int hour;

        public UserUsage(String userId) {
            this.userId = userId;
            this.date = LocalDate.now().toString();
            this.hour = LocalDateTime.now().getHour();
        }

        public UserUsage(String userId, int dailyTokens, int hourlyRequests, String date, int hour) {
            this.userId = userId;
            this.dailyTokens = dailyTokens;
            this.hourlyRequests = hourlyRequests;
            this.date = date;
            this.hour = hour;
        }

        public String userId() { return userId; }
        public int dailyTokens() { return dailyTokens; }
        public int hourlyRequests() { return hourlyRequests; }
        public String date() { return date; }
        public int hour() { return hour; }

        public void addTokens(int tokens) { this.dailyTokens += tokens; }
        public void addRequest() { this.hourlyRequests++; }

        /**
         * Check if usage exceeds budget.
         */
        public boolean checkBudget(HarnessConfig.CostControlConfig config) {
            return dailyTokens <= config.getDailyTokenLimit() &&
                   hourlyRequests <= config.getHourlyRequestLimit();
        }
    }

    // -------------------------------------------------------------------------
    // Global Usage
    // -------------------------------------------------------------------------

    /**
     * Global usage statistics.
     */
    class GlobalUsage {
        private double dailyCostUsd;
        private int dailyTokens;
        private String date;

        public GlobalUsage() {
            this.date = LocalDate.now().toString();
        }

        public GlobalUsage(double dailyCostUsd, int dailyTokens, String date) {
            this.dailyCostUsd = dailyCostUsd;
            this.dailyTokens = dailyTokens;
            this.date = date;
        }

        public double dailyCostUsd() { return dailyCostUsd; }
        public int dailyTokens() { return dailyTokens; }
        public String date() { return date; }

        public void addCost(double cost) { this.dailyCostUsd += cost; }
        public void addTokens(int tokens) { this.dailyTokens += tokens; }

        /**
         * Check if usage exceeds budget.
         */
        public boolean checkBudget(HarnessConfig.CostControlConfig config) {
            return dailyCostUsd <= config.getGlobalDailyBudgetUsd();
        }
    }
}

// -------------------------------------------------------------------------
// In-Memory Implementation
// -------------------------------------------------------------------------

/**
 * In-memory cost storage.
 *
 * Suitable for single-process applications. Data is lost on restart.
 */
class InMemoryCostStorage implements CostStorage {

    private static final Logger logger = LoggerFactory.getLogger(InMemoryCostStorage.class);

    private final Map<String, UserUsage> userUsageMap = new ConcurrentHashMap<>();
    private GlobalUsage globalUsage = new GlobalUsage();
    private String lastResetDate = "";

    private String getCurrentDate() {
        return LocalDate.now().toString();
    }

    private int getCurrentHour() {
        return LocalDateTime.now().getHour();
    }

    private void checkAndResetDaily() {
        String currentDate = getCurrentDate();
        if (!currentDate.equals(lastResetDate)) {
            resetDaily();
            lastResetDate = currentDate;
        }
    }

    @Override
    public UserUsage getUserUsage(String userId) {
        checkAndResetDaily();

        return userUsageMap.computeIfAbsent(userId, id -> new UserUsage(id));
    }

    @Override
    public UserUsage recordUserUsage(String userId, int inputTokens, int outputTokens, boolean request) {
        checkAndResetDaily();

        UserUsage usage = userUsageMap.computeIfAbsent(userId, id -> new UserUsage(id));

        // Check if hour changed
        int currentHour = getCurrentHour();
        if (currentHour != usage.hour()) {
            usage = new UserUsage(userId, usage.dailyTokens(), 0, usage.date(), currentHour);
            userUsageMap.put(userId, usage);
        }

        usage.addTokens(inputTokens + outputTokens);
        if (request) {
            usage.addRequest();
        }

        return usage;
    }

    @Override
    public GlobalUsage getGlobalUsage() {
        checkAndResetDaily();
        return globalUsage;
    }

    @Override
    public GlobalUsage recordGlobalUsage(double costUsd, int tokens) {
        checkAndResetDaily();

        globalUsage.addCost(costUsd);
        globalUsage.addTokens(tokens);

        return globalUsage;
    }

    @Override
    public void resetDaily() {
        userUsageMap.clear();
        globalUsage = new GlobalUsage();
        lastResetDate = getCurrentDate();
        logger.debug("Daily cost storage reset");
    }
}

// -------------------------------------------------------------------------
// SQLite Implementation
// -------------------------------------------------------------------------

/**
 * SQLite-based cost storage.
 *
 * Provides persistent storage for multi-process applications.
 */
class SQLiteCostStorage implements CostStorage {

    private static final Logger logger = LoggerFactory.getLogger(SQLiteCostStorage.class);

    private final String dbPath;
    private boolean initialized = false;

    public SQLiteCostStorage(String dbPath) {
        this.dbPath = dbPath;
        initDb();
    }

    public SQLiteCostStorage() {
        this(".harness/costs.db");
    }

    private void initDb() {
        if (initialized) return;

        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + dbPath)) {
            conn.createStatement().execute("""
                CREATE TABLE IF NOT EXISTS user_usage (
                    user_id TEXT,
                    date TEXT,
                    hour INTEGER,
                    daily_tokens INTEGER DEFAULT 0,
                    hourly_requests INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, date)
                )
            """);

            conn.createStatement().execute("""
                CREATE TABLE IF NOT EXISTS global_usage (
                    date TEXT PRIMARY KEY,
                    daily_cost_usd REAL DEFAULT 0,
                    daily_tokens INTEGER DEFAULT 0
                )
            """);

            initialized = true;
        } catch (SQLException e) {
            logger.error("Failed to initialize cost storage database: {}", e.getMessage());
        }
    }

    private String getCurrentDate() {
        return LocalDate.now().toString();
    }

    private int getCurrentHour() {
        return LocalDateTime.now().getHour();
    }

    @Override
    public UserUsage getUserUsage(String userId) {
        String date = getCurrentDate();
        int hour = getCurrentHour();

        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + dbPath)) {
            PreparedStatement stmt = conn.prepareStatement(
                "SELECT daily_tokens, hourly_requests, hour FROM user_usage WHERE user_id = ? AND date = ?"
            );
            stmt.setString(1, userId);
            stmt.setString(2, date);

            ResultSet rs = stmt.executeQuery();
            if (rs.next()) {
                int storedHour = rs.getInt("hour");
                int hourlyRequests = storedHour == hour ? rs.getInt("hourly_requests") : 0;
                return new UserUsage(userId, rs.getInt("daily_tokens"), hourlyRequests, date, hour);
            }

            return new UserUsage(userId);

        } catch (SQLException e) {
            logger.error("Failed to get user usage: {}", e.getMessage());
            return new UserUsage(userId);
        }
    }

    @Override
    public UserUsage recordUserUsage(String userId, int inputTokens, int outputTokens, boolean request) {
        String date = getCurrentDate();
        int hour = getCurrentHour();
        int tokens = inputTokens + outputTokens;

        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + dbPath)) {
            // Check if exists
            PreparedStatement checkStmt = conn.prepareStatement(
                "SELECT daily_tokens, hourly_requests, hour FROM user_usage WHERE user_id = ? AND date = ?"
            );
            checkStmt.setString(1, userId);
            checkStmt.setString(2, date);
            ResultSet rs = checkStmt.executeQuery();

            if (rs.next()) {
                int storedHour = rs.getInt("hour");
                int hourlyRequests = storedHour == hour ? rs.getInt("hourly_requests") : 0;

                PreparedStatement updateStmt = conn.prepareStatement("""
                    UPDATE user_usage
                    SET daily_tokens = daily_tokens + ?,
                        hourly_requests = ?,
                        hour = ?
                    WHERE user_id = ? AND date = ?
                """);
                updateStmt.setInt(1, tokens);
                updateStmt.setInt(2, hourlyRequests + (request ? 1 : 0));
                updateStmt.setInt(3, hour);
                updateStmt.setString(4, userId);
                updateStmt.setString(5, date);
                updateStmt.execute();
            } else {
                PreparedStatement insertStmt = conn.prepareStatement("""
                    INSERT INTO user_usage (user_id, date, hour, daily_tokens, hourly_requests)
                    VALUES (?, ?, ?, ?, ?)
                """);
                insertStmt.setString(1, userId);
                insertStmt.setString(2, date);
                insertStmt.setInt(3, hour);
                insertStmt.setInt(4, tokens);
                insertStmt.setInt(5, request ? 1 : 0);
                insertStmt.execute();
            }

        } catch (SQLException e) {
            logger.error("Failed to record user usage: {}", e.getMessage());
        }

        return getUserUsage(userId);
    }

    @Override
    public GlobalUsage getGlobalUsage() {
        String date = getCurrentDate();

        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + dbPath)) {
            PreparedStatement stmt = conn.prepareStatement(
                "SELECT daily_cost_usd, daily_tokens FROM global_usage WHERE date = ?"
            );
            stmt.setString(1, date);

            ResultSet rs = stmt.executeQuery();
            if (rs.next()) {
                return new GlobalUsage(rs.getDouble("daily_cost_usd"), rs.getInt("daily_tokens"), date);
            }

            return new GlobalUsage();

        } catch (SQLException e) {
            logger.error("Failed to get global usage: {}", e.getMessage());
            return new GlobalUsage();
        }
    }

    @Override
    public GlobalUsage recordGlobalUsage(double costUsd, int tokens) {
        String date = getCurrentDate();

        try (Connection conn = DriverManager.getConnection("jdbc:sqlite:" + dbPath)) {
            PreparedStatement stmt = conn.prepareStatement("""
                INSERT INTO global_usage (date, daily_cost_usd, daily_tokens)
                VALUES (?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    daily_cost_usd = daily_cost_usd + ?,
                    daily_tokens = daily_tokens + ?
            """);
            stmt.setString(1, date);
            stmt.setDouble(2, costUsd);
            stmt.setInt(3, tokens);
            stmt.setDouble(4, costUsd);
            stmt.setInt(5, tokens);
            stmt.execute();

        } catch (SQLException e) {
            logger.error("Failed to record global usage: {}", e.getMessage());
        }

        return getGlobalUsage();
    }

    @Override
    public void resetDaily() {
        // SQLite automatically handles new dates
    }
}
