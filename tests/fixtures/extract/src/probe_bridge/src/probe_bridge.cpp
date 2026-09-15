// Fixture for tests/extract_golden.py. Deliberately small, and deliberately NOT all-literal:
// ProbeSide below is the "name built from literals plus one identifier" case, which the
// extractor must FLAG with its candidate values rather than declare.

#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float32_multi_array.hpp"
#include "std_msgs/msg/string.hpp"

namespace probe_bridge
{

class ProbeSide
{
public:
    ProbeSide(rclcpp::Node *node, const std::string &side)
    {
        // Name is "/probe/" + side + "/state". Not a literal: the extractor must emit a FLAG
        // carrying the candidate names, and must NOT emit a declaration for it.
        state_pub_ = node->create_publisher<std_msgs::msg::Float32MultiArray>(
            "/probe/" + side + "/state", 1);

        cmd_sub_ = node->create_subscription<std_msgs::msg::Float32MultiArray>(
            "/probe/" + side + "/cmd", 10,
            [](const std_msgs::msg::Float32MultiArray &) {});
    }

private:
    rclcpp::Publisher<std_msgs::msg::Float32MultiArray>::SharedPtr state_pub_;
    rclcpp::Subscription<std_msgs::msg::Float32MultiArray>::SharedPtr cmd_sub_;
};

class ProbeBridge : public rclcpp::Node
{
public:
    ProbeBridge() : Node("probe_bridge_main")
    {
        this->declare_parameter("interface", "eth0");

        // Both literal: name and type sit in the same call, so both are emitted.
        status_pub_ = this->create_publisher<std_msgs::msg::String>("/probe/status", 10);
        reset_sub_ = this->create_subscription<std_msgs::msg::String>(
            "/probe/reset", 10, [](const std_msgs::msg::String &) {});

        // Two construction sites, both literal -- this is the evidence the FLAG reports.
        left_ = std::make_unique<ProbeSide>(this, "left");
        right_ = std::make_unique<ProbeSide>(this, "right");
    }

private:
    std::unique_ptr<ProbeSide> left_;
    std::unique_ptr<ProbeSide> right_;
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr status_pub_;
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr reset_sub_;
};

}  // namespace probe_bridge

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<probe_bridge::ProbeBridge>());
    rclcpp::shutdown();
    return 0;
}
