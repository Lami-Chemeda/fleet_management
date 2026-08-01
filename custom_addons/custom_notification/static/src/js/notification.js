/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
  Component,
  onWillStart,
  useState,
  onMounted,
  onWillUnmount,
} from "@odoo/owl";
import { session } from "@web/session";

function getRelativeTime(date) {
  const now = new Date();
  const past = new Date(date + "Z");
  const diffInMilliseconds = now - past;

  const seconds = Math.floor(diffInMilliseconds / 1000);
  const minutes = Math.floor(diffInMilliseconds / (1000 * 60));
  const hours = Math.floor(diffInMilliseconds / (1000 * 60 * 60));
  const days = Math.floor(diffInMilliseconds / (1000 * 60 * 60 * 24));

  if (seconds < 60) return `${seconds} seconds ago`;
  if (minutes < 60) return `${minutes} minutes ago`;
  if (hours < 24) return `${hours} hours ago`;
  return `${days} days ago`;
}

export class Notification extends Component {
  static template = "custom_notification.Notification"; // Ensure template name matches XML

  setup() {
    this.state = useState({
      notifications: [],
      unreadCount: 0,
      showDropdown: false,
      limit: 5,
      offset: 0,
      hasMore: true,
    });

    this.orm = useService("orm");
    this.actionService = useService("action");
    const userId = session.storeData.Store.settings.user_id.id;

    onWillStart(async () => {
      // Check if user service is available
      if (!session.storeData.Store.settings.user_id.id) {
        console.error("User service is not available");
        return;
      }
      await this.fetchNotifications(
        session.storeData.Store.settings.user_id.id
      );
    });

    onMounted(() => {
      document.addEventListener("click", this.onOutsideClick.bind(this));
    });

    onWillUnmount(() => {
      document.removeEventListener("click", this.onOutsideClick);
    });
  }

  async onClickNavbarMenu() {
    this.state.showDropdown = !this.state.showDropdown;
    if (this.state.showDropdown) {
      this.state.offset = 0; // Reset offset when opening dropdown
      this.state.hasMore = true;
      await this.fetchNotifications(
        session.storeData.Store.settings.user_id.id
      );
    }
  }

  async fetchNotifications(currentUserId) {
    try {
      if (!currentUserId) {
        console.error("User ID is not available", currentUserId);
        return;
      }

      const [allNotifications, notifications] = await Promise.all([
        this.orm.searchRead(
          "custom.notification",
          [
            ["user_id", "=", currentUserId],
            ["is_read", "=", false],
          ],
          [
            "id",
            "title",
            "message",
            "create_date",
            "action_model",
            "action_id",
            "action_res_id",
            "action_view_mode",
            "action_company_id",
          ]
        ),
        this.orm.searchRead(
          "custom.notification",
          [
            ["user_id", "=", currentUserId],
            ["is_read", "=", false],
          ],
          [
            "id",
            "title",
            "message",
            "create_date",
            "action_model",
            "action_id",
            "action_res_id",
            "action_view_mode",
            "action_company_id",
          ],
          {
            order: "create_date desc",
            limit: this.state.limit,
            offset: this.state.offset,
          }
        ),
      ]);

      this.state.notifications = notifications.map((notification) => ({
        ...notification,
        relativeTime: getRelativeTime(notification.create_date),
      }));
      this.state.unreadCount = allNotifications.length;
      this.state.hasMore =
        this.state.offset + this.state.limit < allNotifications.length;
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
    }
  }

  async onClickSeeMore() {
    this.state.offset += this.state.limit;
    await this.fetchNotifications(session.storeData.Store.settings.user_id.id);
  }

  async markAsRead(notificationId) {
    try {
      await this.orm.write("custom.notification", [notificationId], {
        is_read: true,
      });
      await this.fetchNotifications(
        session.storeData.Store.settings.user_id.id
      );
    } catch (error) {
      console.error("Failed to mark notification as read:", error);
    }
  }

  async onClickNotification(notification) {
    try {
      if (!notification?.id) {
        console.warn("Notification id missing, skipping mark as read");
      } else {
        await this.markAsRead(notification.id);
      }
      this.state.showDropdown = false;
      if (
        notification.action_model &&
        notification.action_res_id &&
        notification.action_id &&
        notification.action_view_mode
      ) {
        await this.actionService.doAction({
          type: "ir.actions.act_window",
          res_model: notification.action_model,
          res_id: notification.action_res_id,
          views: [[false, notification.action_view_mode]],
          target: "current",
          context: {
            active_id: notification.action_res_id,
            active_ids: [notification.action_res_id],
            active_model: notification.action_model,
            allowed_company_ids: [notification.action_company_id],
          },
        });
        console.log("Action performed successfully");
      } else {
        console.warn(
          "Incomplete action metadata in notification:",
          notification
        );
      }
    } catch (error) {
      console.error("Failed to handle notification click:", error);
    }
  }

  onOutsideClick(ev) {
    const dropdown = document.querySelector(".o-main-components-container");
    const toggleButton = document.querySelector(".o_NavbarMenu_toggler");

    if (
      this.state.showDropdown &&
      dropdown &&
      toggleButton &&
      !dropdown.contains(ev.target) &&
      !toggleButton.contains(ev.target)
    ) {
      this.state.showDropdown = false;
      this.state.offset = 0;
      this.state.hasMore = true;
    }
  }
}

registry
  .category("systray")
  .add(
    "custom_notification.Notification",
    { Component: Notification },
    { sequence: 30 }
  );
