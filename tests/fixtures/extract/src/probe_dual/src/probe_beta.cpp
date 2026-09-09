// Fixture for tests/extract_golden.py -- the SECOND executable of probe_dual.
//
// Same shape as probe_alpha.cpp but with the other spelling of the node factory,
// std::make_shared<rclcpp::Node>(...), and a subscriber instead of a publisher. Its
// interface must land on `probe_beta` and must NOT appear under `probe_alpha`.

#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);

    auto node = std::make_shared<rclcpp::Node>("probe_beta_node");

    auto beta_sub = node->create_subscription<std_msgs::msg::String>(
        "/probe/beta", 10, [](const std_msgs::msg::String &) {});

    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
