/**
 * Triggers module - Event-driven goal execution.
 *
 * <p>This module provides a trigger system for scheduling and event-driven execution:</p>
 * <ul>
 *   <li>{@link com.harness.triggers.Trigger} - Abstract base class for all triggers</li>
 *   <li>{@link com.harness.triggers.CronTrigger} - Cron expression scheduling</li>
 *   <li>{@link com.harness.triggers.IntervalTrigger} - Fixed interval scheduling</li>
 *   <li>{@link com.harness.triggers.TriggerManager} - Central manager for triggers</li>
 * </ul>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * TriggerManager manager = new TriggerManager(agent);
 *
 * // Cron trigger - daily at 9:00
 * CronTrigger daily = new CronTrigger(
 *     "0 9 * * *",
 *     new TriggerAction.Builder()
 *         .goal("Generate daily report")
 *         .build()
 * );
 * manager.register(daily);
 *
 * // Interval trigger - every 5 minutes
 * IntervalTrigger health = new IntervalTrigger(
 *     300,
 *     new TriggerAction.Builder()
 *         .goal("Health check")
 *         .build()
 * );
 * manager.register(health);
 *
 * manager.start().join();
 * }</pre>
 */
package com.harness.triggers;
