// Fixture for tests/extract_golden.py.
//
// Two things under test here. (1) This node is built in main() with no class deriving from
// rclcpp::Node, so its name lives only in the make_shared call -- a literal, and therefore
// something the extractor must read. (2) Its publisher belongs to the `probe_alpha`
// executable and to nothing else.

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);

    auto node = rclcpp::Node::make_shared("probe_alpha_node");

    auto alpha_pub = node->create_publisher<std_msgs::msg::String>("/probe/alpha", 10);

    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
