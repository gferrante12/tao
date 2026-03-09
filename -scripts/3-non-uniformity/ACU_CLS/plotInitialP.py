import numpy as np
import matplotlib.pyplot as plt

def read_data(file_path):
    xs = []
    ys = []
    zs = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip() == '':
                continue
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            try:
                x = float(parts[2])
                y = float(parts[3])
                z = float(parts[4])
            except:
                continue
            xs.append(x)
            ys.append(y)
            zs.append(z)
    return np.array(xs), np.array(ys), np.array(zs)

def cartesian_to_spherical(xs, ys, zs):
    R = np.sqrt(xs**2 + ys**2 + zs**2)
    # 为防止除零，先处理R=0的情况
    with np.errstate(divide='ignore', invalid='ignore'):
        theta = np.arccos(np.clip(zs / R, -1.0, 1.0))  # 极角 θ [0, π]
    phi = np.arctan2(ys, xs)  # 方位角 φ [-π, π]
    # 将 φ 转化为 [0, 2π]
    phi = np.mod(phi, 2*np.pi)
    return R, theta, phi

def plot_projection(x_data, y_data, xlabel, ylabel, title, filename, xlabel_tick_formatter=None, ylabel_tick_formatter=None):
    fig, ax = plt.subplots(figsize=(8,6))
    sc = ax.scatter(x_data, y_data, s=20, alpha=0.7, edgecolors='w')
    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    ax.set_title(title, fontsize=16)
    plt.tight_layout()

    if xlabel_tick_formatter is not None:
        ax.xaxis.set_major_formatter(xlabel_tick_formatter)
    if ylabel_tick_formatter is not None:
        ax.yaxis.set_major_formatter(ylabel_tick_formatter)

    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close(fig)
def plot_yz_projection(y_ACU, z_ACU, y_CLS, z_CLS):
    fig, ax = plt.subplots(figsize=(8,6))
    # 绘制点
    ax.scatter(y_ACU, z_ACU, s=22, label='ACU', alpha=0.7, edgecolors='w', color='red')
    ax.scatter(y_CLS, z_CLS, s=22, label='CLS', alpha=0.7, edgecolors='w', color='blue')
    # 画圆
    circle = plt.Circle((0, 0), 900, color='black', fill=False, linestyle='--', linewidth=1.5)
    ax.add_patch(circle)
    ax.set_xlabel('Y [mm]', fontsize=18)
    ax.set_ylabel('Z [mm]', fontsize=18)
    # ax.set_title('Y-Z Plane Projection of Points', fontsize=16)
    # ax.legend(fontsize=14, loc='upper right', bbox_to_anchor=(1.0, 1.0), borderaxespad=0.0)
    ## legend 没有形状填充和边框
    ax.legend(fontsize=16, loc='upper right', bbox_to_anchor=(1.0, 1.0), borderaxespad=0.0, frameon=False)
    ax.tick_params(labelsize=16)
    # ax.grid(True)
    ax.set_xlim(-1000, 1000)
    ax.set_ylim(-1000, 1000)
    ax.set_aspect('equal')
    plt.tight_layout()
    plt.savefig("YZ_projection.pdf", dpi=300, bbox_inches='tight')
    plt.close(fig)  # 关闭图，释放内存

def plot_xz_projection(x_ACU, z_ACU, x_CLS, z_CLS):
    fig, ax = plt.subplots(figsize=(8,6))
    # 绘制点 
    ax.scatter(x_ACU, z_ACU, s=22, label='ACU', alpha=0.7, edgecolors='w', color='red')
    ax.scatter(x_CLS, z_CLS, s=22, label='CLS', alpha=0.7, edgecolors='w', color='blue')

    # 画圆
    circle = plt.Circle((0, 0), 900, color='black', fill=False, linestyle='--', linewidth=1.5)
    ax.add_patch(circle)
    ax.set_xlabel('X [mm]', fontsize=18)
    ax.set_ylabel('Z [mm]', fontsize=18)
    # ax.set_title('X-Z Plane Projection of Points', fontsize=16)
    ax.legend(fontsize=16, loc='upper right', bbox_to_anchor=(1.0, 1.0), borderaxespad=0.0, frameon=False)
    # ax.legend(fontsize=14)
    # ax.grid(True)
    ax.set_xlim(-1000, 1000)
    ax.set_ylim(-1000, 1000)
    ax.set_aspect('equal')
    ## 设置标签大小
    ax.tick_params(labelsize=16)
    plt.tight_layout()
    plt.savefig("XZ_projection.pdf", dpi=300, bbox_inches='tight')
    plt.close(fig)

def main():
    # 真实的数据位置
    # file_ACU = "/junofs/users/shihangyu/workspace/reconstruction/CreateCoordinnate/ACU_Ge43p.txt"
    # file_CLS = "/junofs/users/shihangyu/workspace/reconstruction/CreateCoordinnate/CLSPosition_20251223_45deg.txt"
    # 设计的数据位置
    file_ACU = "/junofs/users/shihangyu/workspace/reconstruction/CreateCoordinnate/ACU_Ge43p.txt"
    file_CLS = "/junofs/users/shihangyu/workspace/reconstruction/CreateCoordinnate/CLS_40.txt"


    x_ACU, y_ACU, z_ACU = read_data(file_ACU)
    x_CLS, y_CLS, z_CLS = read_data(file_CLS)

    # 之前的YZ和XZ投影绘制函数，你也可以添加这里，省略了重复代码

    # 计算球坐标
    R_ACU, theta_ACU, phi_ACU = cartesian_to_spherical(x_ACU, y_ACU, z_ACU)
    R_CLS, theta_CLS, phi_CLS = cartesian_to_spherical(x_CLS, y_CLS, z_CLS)

    # 合并数据绘制投影（分别绘制ACU和CLS两类数据点，颜色区分）
    def plot_with_labels(x1, y1, x2, y2, xlabel, ylabel, title, filename):
        fig, ax = plt.subplots(figsize=(8,6))
        ax.scatter(x1, y1, s=20, label='ACU', alpha=0.7, edgecolors='w', color='red')
        ax.scatter(x2, y2, s=20, label='CLS', alpha=0.7, edgecolors='w', color='blue')
        ax.set_xlabel(xlabel, fontsize=14)
        ax.set_ylabel(ylabel, fontsize=14)
        ax.set_title(title, fontsize=16)
        ax.legend(fontsize=12)
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close(fig)

    # R - theta 投影（theta单位是弧度，这里可以转成角度方便阅读）
    plot_with_labels(
        R_ACU, np.degrees(theta_ACU),
        R_CLS, np.degrees(theta_CLS),
        xlabel='Radius R [mm]',
        ylabel='Polar Angle θ [deg]',
        title='R - θ Projection',
        filename='R_theta_projection.png'
    )

    # R - phi 投影（φ转成角度）
    plot_with_labels(
        R_ACU, np.degrees(phi_ACU),
        R_CLS, np.degrees(phi_CLS),
        xlabel='Radius R [mm]',
        ylabel='Azimuthal Angle φ [deg]',
        title='R - φ Projection',
        filename='R_phi_projection.png'
    )

    # phi - theta 投影
    plot_with_labels(
        np.degrees(phi_ACU), np.degrees(theta_ACU),
        np.degrees(phi_CLS), np.degrees(theta_CLS),
        xlabel='Azimuthal Angle φ [deg]',
        ylabel='Polar Angle θ [deg]',
        title='φ - θ Projection',
        filename='phi_theta_projection.png'
    )
    plot_yz_projection(y_ACU, z_ACU, y_CLS, z_CLS)
    plot_xz_projection(x_ACU, z_ACU, x_CLS, z_CLS)
if __name__ == "__main__":
    main()
