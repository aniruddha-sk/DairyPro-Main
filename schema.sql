-- ===============================================================
-- DAIRYPRO / DAIRYMITRA - COMPLETE DATABASE TABLE STRUCTURE
-- Source: User-provided Railway MySQL dump
-- Database: dairymitra
-- Server version in source dump: MySQL 9.7.4
-- MySQL dump client: 8.0.45
--
-- Contains all 32 CREATE TABLE statements with columns, data types,
-- defaults, primary keys, unique keys, indexes, foreign keys,
-- check constraints, engine, charset, collation and AUTO_INCREMENT.
--
-- IMPORTANT:
-- 1) This file creates table structures only; it does NOT insert data.
-- 2) It does NOT drop or overwrite existing tables.
-- 3) Run it in an EMPTY database/schema named dairymitra (or change USE).
-- 4) If a table already exists, its CREATE TABLE statement will return
--    'Table already exists'. Do not add DROP TABLE unless you intend
--    to destroy existing data.
-- 5) Foreign-key checks are temporarily disabled so the source dump's
--    original table order can be preserved. They are re-enabled at end.
-- ===============================================================

CREATE DATABASE IF NOT EXISTS `dairymitra`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
USE `dairymitra`;

SET FOREIGN_KEY_CHECKS = 0;
SET UNIQUE_CHECKS = 0;


-- ---------------------------------------------------------------
-- 01/32 TABLE: advance
-- ---------------------------------------------------------------
CREATE TABLE `advance` (
  `id` int NOT NULL AUTO_INCREMENT,
  `vendor_id` int DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  `date` date DEFAULT NULL,
  `amount` float NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_advance` (`vendor_id`,`user_id`,`date`),
  KEY `idx_advance_vendor_date` (`vendor_id`,`user_id`,`date`),
  CONSTRAINT `advance_ibfk_1` FOREIGN KEY (`vendor_id`, `user_id`) REFERENCES `vendors` (`vendor_id`, `user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=162 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 02/32 TABLE: advance_backup_before_migration
-- ---------------------------------------------------------------
CREATE TABLE `advance_backup_before_migration` (
  `id` int NOT NULL DEFAULT '0',
  `vendor_id` int DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  `date` date DEFAULT NULL,
  `amount` float NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 03/32 TABLE: advance_transactions
-- ---------------------------------------------------------------
CREATE TABLE `advance_transactions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `vendor_id` int NOT NULL,
  `user_id` int NOT NULL,
  `transaction_type` enum('advance','deduction') NOT NULL,
  `amount` decimal(12,2) NOT NULL,
  `transaction_date` date NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `legacy_advance_id` int DEFAULT NULL,
  `client_request_id` varchar(64) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_legacy_advance_id` (`legacy_advance_id`),
  UNIQUE KEY `uq_advance_request` (`user_id`,`client_request_id`),
  KEY `idx_advance_vendor_date` (`vendor_id`,`user_id`,`transaction_date`),
  KEY `idx_advance_user_date` (`user_id`,`transaction_date`),
  KEY `idx_advance_vendor_type_date` (`vendor_id`,`user_id`,`transaction_type`,`transaction_date`),
  CONSTRAINT `fk_advance_vendor` FOREIGN KEY (`vendor_id`, `user_id`) REFERENCES `vendors` (`vendor_id`, `user_id`) ON DELETE CASCADE,
  CONSTRAINT `chk_advance_amount` CHECK ((`amount` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=641 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 04/32 TABLE: bank_settings
-- ---------------------------------------------------------------
CREATE TABLE `bank_settings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `account_holder_name` varchar(150) NOT NULL,
  `bank_name` varchar(100) NOT NULL,
  `branch_name` varchar(100) DEFAULT NULL,
  `account_no` varchar(50) NOT NULL,
  `ifsc_code` varchar(20) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `bank_settings_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 05/32 TABLE: customer_notifications
-- ---------------------------------------------------------------
CREATE TABLE `customer_notifications` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `vendor_id` int NOT NULL,
  `type` enum('milk','food_sack','advance') NOT NULL,
  `title` varchar(255) NOT NULL,
  `message` text NOT NULL,
  `is_read` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `ix_notif_vendor_read` (`user_id`,`vendor_id`,`is_read`),
  CONSTRAINT `customer_notifications_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=23342 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 06/32 TABLE: dm_audit_log
-- ---------------------------------------------------------------
CREATE TABLE `dm_audit_log` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `actor_role` varchar(10) NOT NULL,
  `actor_id` int DEFAULT NULL,
  `action` varchar(60) NOT NULL,
  `target_type` varchar(40) DEFAULT NULL,
  `target_id` varchar(64) DEFAULT NULL,
  `old_values` json DEFAULT NULL,
  `new_values` json DEFAULT NULL,
  `request_id` varchar(32) DEFAULT NULL,
  `ip` varchar(45) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_audit_tenant_time` (`user_id`,`created_at`),
  KEY `ix_audit_target` (`target_type`,`target_id`)
) ENGINE=InnoDB AUTO_INCREMENT=163 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 07/32 TABLE: dm_challenges
-- ---------------------------------------------------------------
CREATE TABLE `dm_challenges` (
  `id` char(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `purpose` varchar(20) NOT NULL,
  `account_key` char(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `otp_hash` char(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `payload` text NOT NULL,
  `expires_at` bigint NOT NULL,
  `attempts` int NOT NULL DEFAULT '0',
  `consumed` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_dm_challenge_account` (`account_key`,`purpose`),
  KEY `ix_dm_challenge_expiry` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 08/32 TABLE: dm_otp_cooldowns
-- ---------------------------------------------------------------
CREATE TABLE `dm_otp_cooldowns` (
  `account_key` char(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `expires_at` bigint NOT NULL,
  PRIMARY KEY (`account_key`),
  KEY `ix_dm_cooldown_expiry` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 09/32 TABLE: dm_outbox
-- ---------------------------------------------------------------
CREATE TABLE `dm_outbox` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `kind` varchar(20) NOT NULL,
  `payload` mediumtext NOT NULL,
  `attempts` int NOT NULL DEFAULT '0',
  `available_at` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_dm_outbox_available` (`available_at`,`id`),
  KEY `ix_dm_outbox_tenant` (`user_id`),
  CONSTRAINT `fk_dm_outbox_owner` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 10/32 TABLE: dm_rate_limits
-- ---------------------------------------------------------------
CREATE TABLE `dm_rate_limits` (
  `bucket_key` char(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `hits` int NOT NULL,
  `expires_at` bigint NOT NULL,
  PRIMARY KEY (`bucket_key`),
  KEY `ix_dm_limit_expiry` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 11/32 TABLE: dm_sessions
-- ---------------------------------------------------------------
CREATE TABLE `dm_sessions` (
  `sid` char(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `payload` mediumtext NOT NULL,
  `version` bigint NOT NULL,
  `expires_at` bigint NOT NULL,
  PRIMARY KEY (`sid`),
  KEY `ix_dm_session_expiry` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 12/32 TABLE: dp_payment_attempts
-- ---------------------------------------------------------------
CREATE TABLE `dp_payment_attempts` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `order_id` bigint NOT NULL,
  `event` varchar(30) NOT NULL,
  `razorpay_payment_id` varchar(40) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  `detail` varchar(500) DEFAULT NULL,
  `ip` varchar(45) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_dp_attempt_order` (`order_id`,`created_at`),
  CONSTRAINT `fk_dp_attempt_order` FOREIGN KEY (`order_id`) REFERENCES `dp_payment_orders` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 13/32 TABLE: dp_payment_orders
-- ---------------------------------------------------------------
CREATE TABLE `dp_payment_orders` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `plan_code` varchar(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `duration_months` int NOT NULL,
  `amount_paise` int NOT NULL,
  `currency` char(3) NOT NULL DEFAULT 'INR',
  `receipt` varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `razorpay_order_id` varchar(40) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  `razorpay_payment_id` varchar(40) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  `status` enum('created','attempted','pending','paid','failed','cancelled','refunded','partially_refunded') NOT NULL DEFAULT 'created',
  `verified_via` varchar(12) DEFAULT NULL,
  `failure_code` varchar(60) DEFAULT NULL,
  `failure_reason` varchar(255) DEFAULT NULL,
  `refunded_paise` int NOT NULL DEFAULT '0',
  `subscription_id` bigint DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `paid_at` datetime DEFAULT NULL,
  `last_checked_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_dp_order_receipt` (`receipt`),
  UNIQUE KEY `uq_dp_order_rzp` (`razorpay_order_id`),
  UNIQUE KEY `uq_dp_order_payment` (`razorpay_payment_id`),
  KEY `ix_dp_order_user` (`user_id`,`created_at`),
  KEY `ix_dp_order_status` (`status`,`created_at`),
  CONSTRAINT `fk_dp_order_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `chk_dp_order_amount` CHECK ((`amount_paise` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 14/32 TABLE: dp_plans
-- ---------------------------------------------------------------
CREATE TABLE `dp_plans` (
  `id` int NOT NULL AUTO_INCREMENT,
  `code` varchar(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `name` varchar(60) NOT NULL,
  `duration_months` int NOT NULL,
  `price_paise` int NOT NULL,
  `savings_pct` int NOT NULL DEFAULT '0',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `sort_order` int NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_dp_plan_code` (`code`),
  CONSTRAINT `chk_dp_plan_duration` CHECK ((`duration_months` > 0)),
  CONSTRAINT `chk_dp_plan_price` CHECK ((`price_paise` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 15/32 TABLE: dp_reminders
-- ---------------------------------------------------------------
CREATE TABLE `dp_reminders` (
  `user_id` int NOT NULL,
  `reminder_key` varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `shown_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`,`reminder_key`),
  CONSTRAINT `fk_dp_reminder_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 16/32 TABLE: dp_subscriptions
-- ---------------------------------------------------------------
CREATE TABLE `dp_subscriptions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `plan_code` varchar(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `order_id` bigint NOT NULL,
  `status` enum('active','cancelled','refunded') NOT NULL DEFAULT 'active',
  `starts_at` datetime NOT NULL,
  `ends_at` datetime NOT NULL,
  `cancelled_at` datetime DEFAULT NULL,
  `cancel_reason` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_dp_sub_order` (`order_id`),
  KEY `ix_dp_sub_user_end` (`user_id`,`status`,`ends_at`),
  CONSTRAINT `fk_dp_sub_order` FOREIGN KEY (`order_id`) REFERENCES `dp_payment_orders` (`id`),
  CONSTRAINT `fk_dp_sub_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 17/32 TABLE: dp_trials
-- ---------------------------------------------------------------
CREATE TABLE `dp_trials` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `email_hash` char(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `started_at` datetime NOT NULL,
  `ends_at` datetime NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_dp_trial_email` (`email_hash`),
  UNIQUE KEY `uq_dp_trial_user` (`user_id`),
  CONSTRAINT `fk_dp_trial_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 18/32 TABLE: dp_webhook_events
-- ---------------------------------------------------------------
CREATE TABLE `dp_webhook_events` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `event_id` varchar(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `event_type` varchar(60) NOT NULL,
  `razorpay_order_id` varchar(40) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  `razorpay_payment_id` varchar(40) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  `payload` mediumtext NOT NULL,
  `result` varchar(60) DEFAULT NULL,
  `received_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `processed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_dp_webhook_event` (`event_id`),
  KEY `ix_dp_webhook_order` (`razorpay_order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 19/32 TABLE: fat_snf_calculation_settings
-- ---------------------------------------------------------------
CREATE TABLE `fat_snf_calculation_settings` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `calculation_mode` enum('general','fat_snf') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'general',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `changed_by_role` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `warn_low_litres` decimal(10,2) NOT NULL DEFAULT '0.50',
  `warn_high_litres` decimal(10,2) NOT NULL DEFAULT '100.00',
  `warn_deviation_pct` int NOT NULL DEFAULT '60',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_fat_snf_settings_user` (`user_id`),
  KEY `idx_fat_snf_settings_user` (`user_id`),
  CONSTRAINT `fk_fsn_settings_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------
-- 20/32 TABLE: fat_snf_chart_values
-- ---------------------------------------------------------------
CREATE TABLE `fat_snf_chart_values` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `chart_id` int unsigned NOT NULL,
  `fat` decimal(5,2) NOT NULL,
  `snf` decimal(5,2) NOT NULL,
  `rate` decimal(10,2) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_fat_snf_chart_value` (`chart_id`,`fat`,`snf`),
  KEY `idx_fat_snf_values_chart` (`chart_id`),
  KEY `idx_fat_snf_values_lookup` (`chart_id`,`fat`,`snf`),
  KEY `idx_fat_snf_values_fat` (`chart_id`,`fat`),
  KEY `idx_fat_snf_values_snf` (`chart_id`,`snf`),
  CONSTRAINT `fk_fsn_value_chart` FOREIGN KEY (`chart_id`) REFERENCES `fat_snf_charts` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_fat_snf_values_fat` CHECK ((`fat` >= 0)),
  CONSTRAINT `chk_fat_snf_values_rate` CHECK ((`rate` >= 0)),
  CONSTRAINT `chk_fat_snf_values_snf` CHECK ((`snf` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=5026 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------
-- 21/32 TABLE: fat_snf_charts
-- ---------------------------------------------------------------
CREATE TABLE `fat_snf_charts` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `created_by_staff_id` int DEFAULT NULL,
  `chart_name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `milk_type` enum('cow','buffalo','both') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'both',
  `effective_from` date NOT NULL,
  `status` enum('active','inactive') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `fat_min` decimal(5,2) DEFAULT NULL,
  `fat_max` decimal(5,2) DEFAULT NULL,
  `fat_step` decimal(5,2) DEFAULT NULL,
  `snf_min` decimal(5,2) DEFAULT NULL,
  `snf_max` decimal(5,2) DEFAULT NULL,
  `snf_step` decimal(5,2) DEFAULT NULL,
  `std_fat` decimal(5,2) DEFAULT NULL,
  `std_snf` decimal(5,2) DEFAULT NULL,
  `std_rate` decimal(10,2) DEFAULT NULL,
  `fat_rate_step` decimal(10,2) DEFAULT NULL,
  `snf_rate_step` decimal(10,2) DEFAULT NULL,
  `version` int NOT NULL DEFAULT '1',
  `revised_from_chart_id` int unsigned DEFAULT NULL,
  `activated_at` timestamp NULL DEFAULT NULL,
  `deactivated_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_fat_snf_charts_user` (`user_id`),
  KEY `idx_fat_snf_charts_user_type` (`user_id`,`milk_type`),
  KEY `idx_fat_snf_charts_effective` (`user_id`,`milk_type`,`effective_from`),
  KEY `idx_fat_snf_charts_status` (`user_id`,`status`),
  KEY `idx_fat_snf_charts_lookup` (`user_id`,`milk_type`,`status`,`effective_from`),
  CONSTRAINT `fk_fsn_chart_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------
-- 22/32 TABLE: fat_snf_milk_collection
-- ---------------------------------------------------------------
CREATE TABLE `fat_snf_milk_collection` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `vendor_id` int NOT NULL,
  `staff_id` int DEFAULT NULL,
  `chart_id` int unsigned NOT NULL,
  `chart_value_id` int unsigned DEFAULT NULL,
  `collection_date` date NOT NULL,
  `slot` enum('morning','evening') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `milk_type` enum('cow','buffalo') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `fat` decimal(5,2) NOT NULL,
  `snf` decimal(5,2) NOT NULL,
  `quantity` decimal(10,2) NOT NULL,
  `rate` decimal(10,2) NOT NULL,
  `amount` decimal(12,2) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `status` enum('saved','final') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'saved',
  `finalized_at` timestamp NULL DEFAULT NULL,
  `client_request_id` varchar(64) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_fat_snf_collection_entry` (`user_id`,`vendor_id`,`collection_date`,`slot`,`milk_type`),
  UNIQUE KEY `uq_fat_snf_collection_request` (`user_id`,`client_request_id`),
  KEY `idx_fat_snf_collection_user_date` (`user_id`,`collection_date`),
  KEY `idx_fat_snf_collection_vendor_date` (`vendor_id`,`collection_date`),
  KEY `idx_fat_snf_collection_user_vendor_date` (`user_id`,`vendor_id`,`collection_date`),
  KEY `idx_fat_snf_collection_date_slot` (`user_id`,`collection_date`,`slot`),
  KEY `idx_fat_snf_collection_vendor_slot` (`user_id`,`vendor_id`,`collection_date`,`slot`),
  KEY `idx_fat_snf_collection_chart` (`chart_id`),
  KEY `idx_fat_snf_collection_chart_value` (`chart_value_id`),
  KEY `idx_fat_snf_collection_type` (`user_id`,`milk_type`,`collection_date`),
  KEY `idx_fat_snf_collection_status` (`user_id`,`collection_date`,`status`),
  KEY `fk_fsn_entry_vendor` (`vendor_id`,`user_id`),
  KEY `fk_fsn_entry_staff` (`staff_id`),
  CONSTRAINT `fk_fsn_entry_chart` FOREIGN KEY (`chart_id`) REFERENCES `fat_snf_charts` (`id`),
  CONSTRAINT `fk_fsn_entry_chart_value` FOREIGN KEY (`chart_value_id`) REFERENCES `fat_snf_chart_values` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_fsn_entry_staff` FOREIGN KEY (`staff_id`) REFERENCES `staff` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_fsn_entry_vendor` FOREIGN KEY (`vendor_id`, `user_id`) REFERENCES `vendors` (`vendor_id`, `user_id`) ON DELETE CASCADE,
  CONSTRAINT `chk_fat_collection_amount` CHECK ((`amount` >= 0)),
  CONSTRAINT `chk_fat_collection_fat` CHECK ((`fat` >= 0)),
  CONSTRAINT `chk_fat_collection_quantity` CHECK ((`quantity` > 0)),
  CONSTRAINT `chk_fat_collection_rate` CHECK ((`rate` >= 0)),
  CONSTRAINT `chk_fat_collection_snf` CHECK ((`snf` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=235 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------
-- 23/32 TABLE: food_sack
-- ---------------------------------------------------------------
CREATE TABLE `food_sack` (
  `id` int NOT NULL AUTO_INCREMENT,
  `vendor_id` int DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  `date` date DEFAULT NULL,
  `sack_qty` int NOT NULL,
  `sack_rate_id` int NOT NULL,
  `total_cost` float NOT NULL,
  `sack_rate` decimal(10,2) DEFAULT '0.00',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_food` (`vendor_id`,`user_id`,`date`,`sack_rate_id`),
  KEY `sack_rate_id` (`sack_rate_id`),
  KEY `idx_food_vendor_date` (`vendor_id`,`user_id`,`date`),
  KEY `idx_food_user_vendor_date` (`user_id`,`vendor_id`,`date`),
  KEY `idx_food_user_date` (`user_id`,`date`),
  CONSTRAINT `food_sack_ibfk_1` FOREIGN KEY (`vendor_id`, `user_id`) REFERENCES `vendors` (`vendor_id`, `user_id`) ON DELETE CASCADE,
  CONSTRAINT `food_sack_ibfk_2` FOREIGN KEY (`sack_rate_id`) REFERENCES `food_sack_rates` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1673 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 24/32 TABLE: food_sack_rates
-- ---------------------------------------------------------------
CREATE TABLE `food_sack_rates` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `name` varchar(100) NOT NULL,
  `rate` float NOT NULL,
  `date_from` date NOT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `food_sack_rates_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=53 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 25/32 TABLE: milk_collection
-- ---------------------------------------------------------------
CREATE TABLE `milk_collection` (
  `id` int NOT NULL AUTO_INCREMENT,
  `vendor_id` int DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  `date` date DEFAULT NULL,
  `slot` enum('morning','evening') NOT NULL,
  `milk_type` enum('cow','buffalo') NOT NULL,
  `quantity` float NOT NULL,
  `staff_id` int DEFAULT NULL,
  `client_request_id` varchar(64) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_entry` (`vendor_id`,`user_id`,`date`,`slot`,`milk_type`),
  UNIQUE KEY `uq_milk_collection_request` (`user_id`,`client_request_id`),
  KEY `idx_milk_vendor_date` (`vendor_id`,`user_id`,`date`),
  KEY `fk_staff_milk` (`staff_id`),
  KEY `idx_milk_user_date` (`user_id`,`date`),
  CONSTRAINT `fk_staff_milk` FOREIGN KEY (`staff_id`) REFERENCES `staff` (`id`) ON DELETE SET NULL,
  CONSTRAINT `milk_collection_ibfk_1` FOREIGN KEY (`vendor_id`, `user_id`) REFERENCES `vendors` (`vendor_id`, `user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=61580 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 26/32 TABLE: milk_rates
-- ---------------------------------------------------------------
CREATE TABLE `milk_rates` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `animal` enum('cow','buffalo') NOT NULL,
  `rate` float NOT NULL,
  `date_from` date NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_rates_user` (`user_id`,`date_from`),
  CONSTRAINT `milk_rates_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 27/32 TABLE: push_subscriptions
-- ---------------------------------------------------------------
CREATE TABLE `push_subscriptions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `vendor_id` int NOT NULL,
  `endpoint` varchar(700) NOT NULL,
  `p256dh` text NOT NULL,
  `auth` text NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `endpoint` (`endpoint`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `push_subscriptions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 28/32 TABLE: schema_migrations
-- ---------------------------------------------------------------
CREATE TABLE `schema_migrations` (
  `version` varchar(40) NOT NULL,
  `description` varchar(255) NOT NULL,
  `applied_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 29/32 TABLE: staff
-- ---------------------------------------------------------------
CREATE TABLE `staff` (
  `id` int NOT NULL AUTO_INCREMENT,
  `owner_id` int NOT NULL,
  `name` varchar(100) NOT NULL,
  `email` varchar(255) DEFAULT NULL,
  `password` varchar(255) NOT NULL,
  `vehicle_number` varchar(20) DEFAULT NULL,
  `role` enum('driver','manager') DEFAULT 'driver',
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `preferred_language` varchar(5) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  KEY `owner_id` (`owner_id`),
  CONSTRAINT `staff_ibfk_1` FOREIGN KEY (`owner_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=50 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 30/32 TABLE: users
-- ---------------------------------------------------------------
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `dairy_name` varchar(255) DEFAULT NULL,
  `is_verified` tinyint(1) DEFAULT '0',
  `otp` varchar(10) DEFAULT NULL,
  `otp_expiry` datetime DEFAULT NULL,
  `reset_token` varchar(255) DEFAULT NULL,
  `reset_token_expiry` datetime DEFAULT NULL,
  `otp_code` varchar(6) DEFAULT NULL,
  `otp_created_at` datetime DEFAULT NULL,
  `security_password_hash` varchar(255) DEFAULT NULL,
  `security_otp` varchar(6) DEFAULT NULL,
  `security_otp_expiry` datetime DEFAULT NULL,
  `dairy_code` varchar(20) DEFAULT NULL,
  `preferred_language` varchar(5) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `dairy_code` (`dairy_code`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 31/32 TABLE: vendor_milk_rates
-- ---------------------------------------------------------------
CREATE TABLE `vendor_milk_rates` (
  `id` int NOT NULL AUTO_INCREMENT,
  `vendor_id` int NOT NULL,
  `user_id` int NOT NULL,
  `cow_rate` decimal(6,2) DEFAULT NULL,
  `buffalo_rate` decimal(6,2) DEFAULT NULL,
  `date_from` date NOT NULL,
  PRIMARY KEY (`id`),
  KEY `vendor_id` (`vendor_id`,`user_id`),
  KEY `idx_vendor_rates_user_date` (`user_id`,`date_from`),
  CONSTRAINT `vendor_milk_rates_ibfk_1` FOREIGN KEY (`vendor_id`, `user_id`) REFERENCES `vendors` (`vendor_id`, `user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=71 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------
-- 32/32 TABLE: vendors
-- ---------------------------------------------------------------
CREATE TABLE `vendors` (
  `id` int NOT NULL AUTO_INCREMENT,
  `vendor_id` int NOT NULL,
  `name` varchar(100) NOT NULL,
  `name_en` varchar(255) DEFAULT NULL,
  `address` text,
  `milk_type` enum('cow','buffalo','both') DEFAULT 'cow',
  `phone` varchar(15) DEFAULT NULL,
  `user_id` int NOT NULL,
  `ifsc_code` varchar(20) DEFAULT NULL,
  `account_no` varchar(30) DEFAULT NULL,
  `preferred_language` varchar(5) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_vendor_per_user` (`vendor_id`,`user_id`),
  KEY `idx_vendor_user` (`user_id`),
  CONSTRAINT `vendors_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=394 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET UNIQUE_CHECKS = 1;
SET FOREIGN_KEY_CHECKS = 1;

-- ===============================================================
-- END: 32 TABLE DEFINITIONS
-- ===============================================================
